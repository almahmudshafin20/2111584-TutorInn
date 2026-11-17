import { mkdtemp, rm, writeFile } from "node:fs/promises";
import { createRequire } from "node:module";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { rspack } from "@rspack/core";

const require = createRequire(import.meta.url);

export async function loadWithRspack({ source, aliases = {} }) {
  const directory = await mkdtemp(join(tmpdir(), "tutorinn-rspack-test-"));
  const entry = join(directory, "entry.mjs");
  const aliasEntries = {};

  try {
    await writeFile(entry, source, "utf8");
    for (const [request, contents] of Object.entries(aliases)) {
      const mockPath = join(directory, `mock-${Object.keys(aliasEntries).length}.mjs`);
      await writeFile(mockPath, contents, "utf8");
      aliasEntries[`${request}$`] = mockPath;
    }

    const compiler = rspack({
      context: process.cwd(),
      mode: "development",
      target: "node",
      entry,
      output: { path: directory, filename: "bundle.cjs", library: { type: "commonjs2" } },
      resolve: { extensions: [".tsx", ".ts", ".jsx", ".js", ".json"], alias: aliasEntries },
      module: {
        rules: [{
          test: /\.(?:js|mjs|jsx|ts|tsx)$/,
          exclude: /node_modules/,
          loader: "builtin:swc-loader",
          options: {
            jsc: {
              parser: { syntax: "typescript", tsx: true },
              transform: { react: { runtime: "automatic" } },
            },
          },
        }],
      },
      externalsPresets: { node: true },
      externals: ({ request }, callback) => {
        if (request === "react" || request.startsWith("react/") ||
            request === "react-dom" || request.startsWith("react-dom/")) {
          callback(null, `commonjs ${request}`);
          return;
        }
        callback();
      },
    });

    const result = await new Promise(resolvePromise => {
      compiler.run((error, stats) => resolvePromise({ error, stats }));
    });
    const closeError = await new Promise(resolvePromise => {
      compiler.close(error => resolvePromise(error));
    });
    if (result.error) throw result.error;
    if (closeError) throw closeError;
    if (result.stats?.hasErrors()) {
      throw new Error(result.stats.toString({ all: false, errors: true, errorDetails: true }));
    }

    return {
      exports: require(resolve(directory, "bundle.cjs")),
      cleanup: () => rm(directory, { recursive: true, force: true }),
    };
  } catch (error) {
    await rm(directory, { recursive: true, force: true });
    throw error;
  }
}

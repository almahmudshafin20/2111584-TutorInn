import { existsSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import { rspack } from "@rspack/core";
import { ReactRefreshRspackPlugin } from "@rspack/plugin-react-refresh";

const rootDir = dirname(fileURLToPath(import.meta.url));
const publicDir = resolve(rootDir, "public");

export default (_env, argv) => {
  const isDevelopment = argv.mode !== "production";
  const plugins = [
    new rspack.HtmlRspackPlugin({
      template: resolve(rootDir, "index.html"),
    }),
  ];

  if (existsSync(publicDir)) {
    plugins.push(
      new rspack.CopyRspackPlugin({
        patterns: [{ from: publicDir, to: "." }],
      }),
    );
  }

  if (isDevelopment) {
    plugins.push(new ReactRefreshRspackPlugin());
  }

  return {
    context: rootDir,
    mode: isDevelopment ? "development" : "production",
    entry: "./src/main.tsx",
    output: {
      path: resolve(rootDir, "dist"),
      filename: "assets/[name].[contenthash:8].js",
      chunkFilename: "assets/[name].[contenthash:8].js",
      cssFilename: "assets/[name].[contenthash:8].css",
      assetModuleFilename: "assets/[name].[contenthash:8][ext]",
      publicPath: "/",
      clean: true,
    },
    devtool: isDevelopment ? "eval-cheap-module-source-map" : false,
    resolve: {
      extensions: [".tsx", ".ts", ".jsx", ".js", ".json"],
    },
    module: {
      rules: [
        {
          test: /\.(?:js|mjs|jsx|ts|tsx)$/,
          exclude: /node_modules/,
          loader: "builtin:swc-loader",
          options: {
            jsc: {
              parser: {
                syntax: "typescript",
                tsx: true,
              },
              transform: {
                react: {
                  runtime: "automatic",
                  development: isDevelopment,
                  refresh: isDevelopment,
                },
              },
            },
          },
        },
        {
          test: /\.css$/i,
          type: "css/auto",
        },
        {
          test: /\.(?:png|jpe?g|gif|svg|webp|ico|woff2?|ttf|otf)$/i,
          type: "asset/resource",
        },
      ],
    },
    plugins,
    devServer: {
      host: "127.0.0.1",
      port: 5173,
      hot: true,
      historyApiFallback: true,
      static: existsSync(publicDir)
        ? { directory: publicDir, publicPath: "/" }
        : false,
      proxy: {
        "/api": {
          target: "http://localhost:8000",
          changeOrigin: true,
        },
      },
    },
  };
};

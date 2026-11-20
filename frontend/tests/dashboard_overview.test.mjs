import assert from "node:assert/strict"
import { after, before, test } from "node:test"
import React from "react"
import { renderToStaticMarkup } from "react-dom/server"
import { resolve } from "node:path"
import { loadWithRspack } from "./rspack-test-utils.mjs"

let cleanup
let Overview

before(async () => {
  const loaded = await loadWithRspack({
    source: `
      import * as Overview from ${JSON.stringify(resolve(process.cwd(), "src/components/DashboardOverview.tsx"))};
      export { Overview };
    `,
    aliases: {},
  })
  cleanup = loaded.cleanup
  ;({ Overview } = loaded.exports)
})

after(async () => {
  await cleanup?.()
})

test("progress bar exposes a rounded accessible value and readable summary", () => {
  const markup = renderToStaticMarkup(React.createElement(Overview.DashboardProgress, { label: "Answered", done: 1, total: 3 }))
  assert.match(markup, /role="progressbar"/)
  assert.match(markup, /aria-valuenow="33"/)
  assert.match(markup, /1 of 3 · 33%/)
})

test("progress bar with no items shows zero instead of NaN", () => {
  const markup = renderToStaticMarkup(React.createElement(Overview.DashboardProgress, { label: "Answered", done: 0, total: 0 }))
  assert.match(markup, /aria-valuenow="0"/)
  assert.doesNotMatch(markup, /NaN/)
})

test("stat tiles render their label, value and hint with a tone class", () => {
  const markup = renderToStaticMarkup(React.createElement(Overview.DashboardStat, { label: "Tutor responses", value: 4, hint: "2 awaiting your decision", tone: "warning" }))
  assert.match(markup, /tone-warning/)
  assert.match(markup, /Tutor responses/)
  assert.match(markup, />4</)
  assert.match(markup, /2 awaiting your decision/)
})

test("callouts are announced as status messages", () => {
  const markup = renderToStaticMarkup(React.createElement(Overview.DashboardCallout, null, "Check responses"))
  assert.match(markup, /role="status"/)
  assert.match(markup, /Check responses/)
})

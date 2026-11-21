import assert from "node:assert/strict"
import { after, before, test } from "node:test"
import { resolve } from "node:path"
import { loadWithRspack } from "./rspack-test-utils.mjs"

let cleanup, positions
before(async () => {
  const loaded = await loadWithRspack({ source: `
    import * as positions from ${JSON.stringify(resolve(process.cwd(), "src/components/accountPositions.ts"))};
    export { positions };
  ` })
  cleanup = loaded.cleanup
  ;({ positions } = loaded.exports)
})
after(async () => { await cleanup?.() })

const accounts = [{ id: 101, email: "a@example.com" }, { id: 102, email: "b@example.com" }, { id: 103, email: "c@example.com" }]

function labelsFor(list, page = 0, pageSize = 25) {
  return list.map((row, index) => ({ id: row.id, label: positions.accountPositionLabel("Tutor", page, pageSize, index) }))
}

test("positions are 1-based labels derived from the displayed order", () => {
  assert.deepEqual(labelsFor(accounts).map(item => item.label), ["Tutor 1", "Tutor 2", "Tutor 3"])
})

test("positions shift after a row is deleted while real IDs stay unchanged", () => {
  const remaining = accounts.filter(row => row.id !== 102)
  const after = labelsFor(remaining)
  assert.deepEqual(after, [{ id: 101, label: "Tutor 1" }, { id: 103, label: "Tutor 2" }])
  assert.equal(after.find(item => item.id === 103).label, "Tutor 2")
})

test("positions continue across pages using the page offset", () => {
  assert.equal(positions.accountPositionLabel("Student", 1, 25, 0), "Student 26")
  assert.equal(positions.accountPositionLabel("Student", 2, 10, 4), "Student 25")
})

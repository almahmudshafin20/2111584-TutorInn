// Display-only positions for Admin account lists. Positions are recomputed from the currently displayed
// order every time they are rendered; the database ID is never changed and remains the value used for actions.
export function accountPositionLabel(prefix: string, page: number, pageSize: number, index: number): string {
  return `${prefix} ${page * pageSize + index + 1}`
}

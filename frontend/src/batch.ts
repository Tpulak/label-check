import type { ApplicationFieldName, ApplicationInfo } from "./types/verification"

export type BatchRow = {
  filename: string
  application: ApplicationInfo
}

export type BatchPlanItem = BatchRow & {
  file: File | null
  problem: string | null
}

const REQUIRED_COLUMNS: ApplicationFieldName[] = [
  "brand_name",
  "class_type",
  "alcohol_content",
  "net_contents",
  "producer",
]

const HEADER_NAMES: Record<string, "filename" | ApplicationFieldName> = {
  filename: "filename",
  file: "filename",
  image: "filename",
  image_filename: "filename",
  photo: "filename",
  brand_name: "brand_name",
  brand: "brand_name",
  class_type: "class_type",
  class: "class_type",
  type: "class_type",
  alcohol_content: "alcohol_content",
  alcohol: "alcohol_content",
  abv: "alcohol_content",
  net_contents: "net_contents",
  net: "net_contents",
  size: "net_contents",
  producer: "producer",
  producer_name: "producer",
}

export function readSpreadsheet(text: string): BatchRow[] {
  const table = parseCsv(text)
  if (table.length < 2) {
    throw new Error("The spreadsheet needs a header row and at least one label.")
  }

  const columns = table[0].map((header) => HEADER_NAMES[normalizeHeader(header)] ?? null)
  const missing = ["filename", ...REQUIRED_COLUMNS].filter(
    (name) => !columns.includes(name as "filename" | ApplicationFieldName),
  )
  if (missing.length > 0) {
    throw new Error(
      `Add these columns to the first row: ${missing.join(", ")}.`,
    )
  }

  const seen = new Set<string>()
  return table.slice(1).map((cells, index) => {
    const rowNumber = index + 2
    const filename = cell(cells, columns, "filename")
    if (!filename) {
      throw new Error(`Row ${rowNumber} does not name a photo.`)
    }
    const key = filename.toLowerCase()
    if (seen.has(key)) {
      throw new Error(`Row ${rowNumber} repeats the photo name ${filename}.`)
    }
    seen.add(key)

    const application = {} as ApplicationInfo
    for (const field of REQUIRED_COLUMNS) {
      application[field] = cell(cells, columns, field)
    }
    return { filename, application }
  })
}

export function pairPhotos(rows: BatchRow[], photos: File[]): {
  items: BatchPlanItem[]
  extraPhotos: string[]
} {
  const photosByName = new Map(photos.map((photo) => [photo.name.toLowerCase(), photo]))
  const items = rows.map((row) => {
    const file = photosByName.get(row.filename.toLowerCase()) ?? null
    return {
      ...row,
      file,
      problem: file ? null : `No photo named ${row.filename} was included.`,
    }
  })
  const used = new Set(rows.map((row) => row.filename.toLowerCase()))
  const extraPhotos = photos
    .map((photo) => photo.name)
    .filter((name) => !used.has(name.toLowerCase()))
  return { items, extraPhotos }
}

export function exampleSpreadsheet(): string {
  return [
    "filename,brand_name,class_type,alcohol_content,net_contents,producer",
    'valid-label.png,OLD TOM DISTILLERY,Kentucky Straight Bourbon Whiskey,45%,750 mL,"Old Tom Distillery, Louisville, KY"',
    "",
  ].join("\n")
}

function cell(
  cells: string[],
  columns: Array<"filename" | ApplicationFieldName | null>,
  name: "filename" | ApplicationFieldName,
): string {
  const index = columns.indexOf(name)
  return (cells[index] ?? "").trim()
}

function normalizeHeader(header: string): string {
  return header.trim().toLowerCase().replace(/\s+/g, "_")
}

function parseCsv(text: string): string[][] {
  const rows: string[][] = []
  let row: string[] = []
  let value = ""
  let quoted = false
  const source = text.replace(/^\uFEFF/, "")

  for (let index = 0; index < source.length; index += 1) {
    const character = source[index]
    if (quoted) {
      if (character === '"') {
        if (source[index + 1] === '"') {
          value += '"'
          index += 1
        } else {
          quoted = false
        }
      } else {
        value += character
      }
      continue
    }
    if (character === '"') {
      quoted = true
      continue
    }
    if (character === ",") {
      row.push(value.trim())
      value = ""
      continue
    }
    if (character === "\n" || character === "\r") {
      if (character === "\r" && source[index + 1] === "\n") index += 1
      row.push(value.trim())
      if (row.some((cellValue) => cellValue !== "")) rows.push(row)
      row = []
      value = ""
      continue
    }
    value += character
  }

  row.push(value.trim())
  if (row.some((cellValue) => cellValue !== "")) rows.push(row)
  return rows
}

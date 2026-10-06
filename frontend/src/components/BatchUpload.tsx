import { useRef, useState } from "react"
import { exampleSpreadsheet, pairPhotos, readSpreadsheet, type BatchPlanItem } from "../batch"
import { verifyLabel } from "../services/api"
import BatchResults, { type FinishedLabel } from "./BatchResults"

function BatchUpload() {
  const [spreadsheetName, setSpreadsheetName] = useState<string | null>(null)
  const [photoCount, setPhotoCount] = useState(0)
  const [items, setItems] = useState<BatchPlanItem[]>([])
  const [extraPhotos, setExtraPhotos] = useState<string[]>([])
  const [setupError, setSetupError] = useState<string | null>(null)
  const [isChecking, setIsChecking] = useState(false)
  const [progress, setProgress] = useState<{ current: number; total: number; name: string } | null>(
    null,
  )
  const [finished, setFinished] = useState<FinishedLabel[]>([])
  const [stopped, setStopped] = useState(false)
  const [selectedFilename, setSelectedFilename] = useState<string | null>(null)
  const photosRef = useRef<File[]>([])
  const stopRef = useRef(false)

  function loadSpreadsheet(file: File) {
    file
      .text()
      .then((text) => {
        const rows = readSpreadsheet(text)
        const paired = pairPhotos(rows, photosRef.current)
        setSpreadsheetName(file.name)
        setItems(paired.items)
        setExtraPhotos(paired.extraPhotos)
        setSetupError(null)
        setFinished([])
        setStopped(false)
        setSelectedFilename(null)
      })
      .catch((error: unknown) => {
        setItems([])
        setExtraPhotos([])
        setFinished([])
        setSetupError(error instanceof Error ? error.message : "The spreadsheet could not be read.")
      })
  }

  function handleSpreadsheet(file: File | undefined) {
    if (!file) return
    loadSpreadsheet(file)
  }

  function handlePhotos(files: FileList | null) {
    const photos = files ? Array.from(files) : []
    photosRef.current = photos
    setPhotoCount(photos.length)
    if (items.length === 0) return
    const paired = pairPhotos(
      items.map(({ filename, application }) => ({ filename, application })),
      photos,
    )
    setItems(paired.items)
    setExtraPhotos(paired.extraPhotos)
  }

  async function handleCheck() {
    const ready = items.filter((item) => item.file && !item.problem)
    if (items.length === 0) {
      setSetupError("Add a spreadsheet before checking.")
      return
    }
    if (ready.length === 0) {
      setSetupError("None of the spreadsheet rows have a matching photo.")
      return
    }

    stopRef.current = false
    setStopped(false)
    setIsChecking(true)
    setSetupError(null)
    setSelectedFilename(null)
    setFinished([])

    const completed: FinishedLabel[] = []
    let checked = 0

    for (const item of items) {
      if (stopRef.current) {
        setStopped(true)
        break
      }
      if (!item.file || item.problem) {
        completed.push({ filename: item.filename, error: item.problem, result: null })
        setFinished([...completed])
        continue
      }
      checked += 1
      setProgress({ current: checked, total: ready.length, name: item.filename })
      let next: FinishedLabel
      try {
        next = {
          filename: item.filename,
          error: null,
          result: await verifyLabel(item.file, item.application),
        }
      } catch (error) {
        next = {
          filename: item.filename,
          error: error instanceof Error ? error.message : "This label could not be checked.",
          result: null,
        }
      }
      completed.push(next)
      setFinished([...completed])
    }

    setProgress(null)
    setIsChecking(false)
  }

  function downloadExample() {
    const blob = new Blob([exampleSpreadsheet()], { type: "text/csv" })
    const url = URL.createObjectURL(blob)
    const link = document.createElement("a")
    link.href = url
    link.download = "applications.csv"
    link.click()
    URL.revokeObjectURL(url)
  }

  const percent = progress ? Math.round((progress.current / progress.total) * 100) : 0

  return (
    <div className="batch">
      <section className="card">
        <h2>Many labels</h2>
        <p className="help">
          Add a spreadsheet with one row per label, then add the photos. The photo file name
          must match the filename column.
        </p>
        <p className="help column-help">
          Columns: filename, brand_name, class_type, alcohol_content, net_contents, producer.
        </p>
        <button type="button" className="secondary" onClick={downloadExample}>
          Download an example spreadsheet
        </button>

        <div className="field">
          <label htmlFor="batch-spreadsheet">Spreadsheet</label>
          <input
            id="batch-spreadsheet"
            type="file"
            accept=".csv,text/csv"
            disabled={isChecking}
            onChange={(event) => handleSpreadsheet(event.target.files?.[0])}
          />
          {spreadsheetName ? <p className="file-name">{spreadsheetName}</p> : null}
        </div>

        <div className="field">
          <label htmlFor="batch-photos">Label photos</label>
          <input
            id="batch-photos"
            type="file"
            accept="image/*"
            multiple
            disabled={isChecking}
            onChange={(event) => handlePhotos(event.target.files)}
          />
          <p className="help">
            {photoCount === 0 ? "No photos added yet." : `${photoCount} photos added.`}
          </p>
        </div>

        {items.length > 0 ? (
          <ul className="plan-list">
            {items.map((item) => (
              <li key={item.filename}>
                {item.filename}
                {item.problem ? ` — ${item.problem}` : " — photo found"}
              </li>
            ))}
          </ul>
        ) : null}

        {spreadsheetName && extraPhotos.length > 0 ? (
          <p className="help">
            These photos have no spreadsheet row: {extraPhotos.join(", ")}.
          </p>
        ) : null}

        {setupError ? (
          <p className="error" role="alert">
            {setupError}
          </p>
        ) : null}

        <div className="batch-actions">
          <button type="button" className="primary" disabled={isChecking} onClick={handleCheck}>
            {isChecking ? "Checking..." : "Check these labels"}
          </button>
          {isChecking ? (
            <button
              type="button"
              className="secondary"
              onClick={() => {
                stopRef.current = true
              }}
            >
              Stop
            </button>
          ) : null}
        </div>

        {progress ? (
          <div className="progress-block">
            <p className="help">
              Checking {progress.current} of {progress.total}: {progress.name}
            </p>
            <div
              className="progress-track"
              role="progressbar"
              aria-valuenow={progress.current}
              aria-valuemin={0}
              aria-valuemax={progress.total}
              aria-label="Batch progress"
            >
              <div className="progress-fill" style={{ width: `${percent}%` }} />
            </div>
          </div>
        ) : null}
      </section>

      {finished.length > 0 ? (
        <BatchResults
          items={finished}
          plannedCount={items.length}
          stopped={stopped}
          selectedFilename={selectedFilename}
          onSelect={setSelectedFilename}
        />
      ) : null}
    </div>
  )
}

export default BatchUpload

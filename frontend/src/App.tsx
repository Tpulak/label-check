import { useEffect, useRef, useState } from "react"
import ApplicationForm from "./components/ApplicationForm"
import BatchUpload from "./components/BatchUpload"
import ImageUpload from "./components/ImageUpload"
import VerificationResults from "./components/VerificationResults"
import { verifyLabel } from "./services/api"
import {
  emptyApplication,
  type ApplicationInfo,
  type VerificationResult,
} from "./types/verification"

function App() {
  const [imageFile, setImageFile] = useState<File | null>(null)
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)
  const [fileName, setFileName] = useState<string | null>(null)
  const [imageError, setImageError] = useState<string | null>(null)
  const [requestError, setRequestError] = useState<string | null>(null)
  const [application, setApplication] = useState<ApplicationInfo>(emptyApplication)
  const [isChecking, setIsChecking] = useState(false)
  const [result, setResult] = useState<VerificationResult | null>(null)
  const [mode, setMode] = useState<"one" | "many">("one")
  const resultRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    return () => {
      if (previewUrl) URL.revokeObjectURL(previewUrl)
    }
  }, [previewUrl])

  useEffect(() => {
    if (result) resultRef.current?.scrollIntoView({ behavior: "smooth", block: "start" })
  }, [result])

  function clearResult() {
    setResult(null)
    setRequestError(null)
  }

  function handleSelectFile(file: File) {
    if (!file.type.startsWith("image/")) {
      setImageError("Please choose a photo, such as a JPG or PNG.")
      return
    }

    setImageError(null)
    setImageFile(file)
    setFileName(file.name)
    setPreviewUrl(URL.createObjectURL(file))
    clearResult()
  }

  function handleClearPhoto() {
    setImageFile(null)
    setPreviewUrl(null)
    setFileName(null)
    setImageError(null)
    clearResult()
  }

  function handleChange(field: keyof ApplicationInfo, value: string) {
    setApplication((current) => ({ ...current, [field]: value }))
    clearResult()
  }

  async function handleVerify() {
    if (!imageFile) {
      setImageError("Choose a label photo before verifying.")
      return
    }

    setImageError(null)
    setRequestError(null)
    setResult(null)
    setIsChecking(true)

    try {
      setResult(await verifyLabel(imageFile, application))
    } catch (error) {
      const message =
        error instanceof Error
          ? error.message
          : "The server could not check this label."
      setRequestError(message)
    } finally {
      setIsChecking(false)
    }
  }

  return (
    <div className="page">
      <header className="header">
        <h1>LabelCheck</h1>
        <p>Compare a label photo with the application.</p>
      </header>

      <div className="mode-switch" role="group" aria-label="How many labels to check">
        <button
          type="button"
          className="mode-button"
          aria-pressed={mode === "one"}
          onClick={() => setMode("one")}
        >
          Check one label
        </button>
        <button
          type="button"
          className="mode-button"
          aria-pressed={mode === "many"}
          onClick={() => setMode("many")}
        >
          Check many labels
        </button>
      </div>

      {mode === "many" ? <BatchUpload /> : null}

      {mode === "one" ? (
      <>
      <div className="workspace">
        <ImageUpload
          previewUrl={previewUrl}
          fileName={fileName}
          error={imageError}
          onSelectFile={handleSelectFile}
          onClear={handleClearPhoto}
        />
        <ApplicationForm
          values={application}
          onChange={handleChange}
          onVerify={handleVerify}
          isChecking={isChecking}
        />
      </div>

      {requestError ? (
        <p className="error request-error" role="alert">
          {requestError}
        </p>
      ) : null}

      {result ? (
        <div ref={resultRef}>
          <VerificationResults result={result} />
        </div>
      ) : null}
      </>
      ) : null}
    </div>
  )
}

export default App

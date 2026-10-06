import { useRef, useState } from "react"

type ImageUploadProps = {
  previewUrl: string | null
  fileName: string | null
  error: string | null
  onSelectFile: (file: File) => void
  onClear: () => void
}

function ImageUpload({
  previewUrl,
  fileName,
  error,
  onSelectFile,
  onClear,
}: ImageUploadProps) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [isDragging, setIsDragging] = useState(false)

  function takeFile(file: File | undefined) {
    if (file) onSelectFile(file)
  }

  function clearPhoto() {
    if (inputRef.current) inputRef.current.value = ""
    onClear()
  }

  return (
    <section className="card" aria-labelledby="photo-heading">
      <h2 id="photo-heading">Label photo</h2>
      <p className="help">Choose the photo of the label you want to check.</p>

      <div
        className={isDragging ? "drop-zone dragging" : "drop-zone"}
        onDragOver={(event) => {
          event.preventDefault()
          setIsDragging(true)
        }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={(event) => {
          event.preventDefault()
          setIsDragging(false)
          takeFile(event.dataTransfer.files[0])
        }}
      >
        <label className="file-choice">
          Choose a photo
          <input
            ref={inputRef}
            id="label-photo"
            className="file-input"
            type="file"
            accept="image/*"
            onChange={(event) => takeFile(event.target.files?.[0])}
          />
        </label>
        <p className="help">Or drop a photo here.</p>

        {previewUrl ? (
          <div className="preview">
            <img src={previewUrl} alt="Selected label photo" />
            <p className="file-name">{fileName}</p>
            <button type="button" className="secondary" onClick={clearPhoto}>
              Remove photo
            </button>
          </div>
        ) : null}
      </div>

      {error ? (
        <p className="error" role="alert">
          {error}
        </p>
      ) : null}
    </section>
  )
}

export default ImageUpload

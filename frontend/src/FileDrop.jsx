import { useState } from 'react'
import { FileCheck2, UploadCloud } from 'lucide-react'

const size = (bytes) => (bytes < 1024 * 1024 ? `${Math.max(1, Math.round(bytes / 1024))} KB` : `${(bytes / 1024 / 1024).toFixed(1)} MB`)

/**
 * A drop zone around a real file input: drag files onto it, or click / press Enter to choose.
 * The input stays in the page (visually hidden), so labels, keyboard use and forms work as usual.
 * `files` is what is currently chosen (shown as names), `onFiles` receives an array of File.
 */
export default function FileDrop({ label, hint, accept, multiple = false, files = [], onFiles, inputRef, id }) {
  const [over, setOver] = useState(false)
  const chosen = files.filter(Boolean)

  function onDrop(event) {
    event.preventDefault()
    setOver(false)
    const dropped = [...event.dataTransfer.files]
    if (!dropped.length) return
    const list = multiple ? dropped : dropped.slice(0, 1)
    if (inputRef?.current) {
      try {
        // Keep the input in step with what was dropped (forms and screen readers read it).
        const transfer = new DataTransfer()
        list.forEach((f) => transfer.items.add(f))
        inputRef.current.files = transfer.files
      } catch {
        /* older browsers: the list below still shows the dropped files */
      }
    }
    onFiles(list)
  }

  return (
    <label
      className={`drop${over ? ' drop--over' : ''}${chosen.length ? ' drop--chosen' : ''}`}
      htmlFor={id}
      onDragOver={(e) => {
        e.preventDefault()
        setOver(true)
      }}
      onDragLeave={() => setOver(false)}
      onDrop={onDrop}
    >
      <input
        ref={inputRef}
        id={id}
        className="drop__input"
        type="file"
        accept={accept}
        multiple={multiple}
        aria-label={label}
        onChange={(e) => onFiles([...e.target.files])}
      />
      {chosen.length ? (
        <FileCheck2 size={22} aria-hidden="true" className="drop__icon" />
      ) : (
        <UploadCloud size={22} aria-hidden="true" className="drop__icon" />
      )}
      <span className="drop__text">
        {chosen.length ? (
          <>
            <strong>{chosen.length === 1 ? chosen[0].name : `${chosen.length} files chosen`}</strong>
            <span className="drop__hint">
              {chosen.length === 1
                ? `${size(chosen[0].size)} · drop another file or click to change`
                : chosen.map((f) => f.name).join(', ')}
            </span>
          </>
        ) : (
          <>
            <strong>
              Drag {multiple ? 'files' : 'a file'} here or <span className="drop__link">choose {multiple ? 'files' : 'a file'}</span>
            </strong>
            {hint && <span className="drop__hint">{hint}</span>}
          </>
        )}
      </span>
    </label>
  )
}

import React, { useRef, useState, useCallback } from 'react'
import './PhotoUpload.css'

/**
 * Drag-and-drop + click-to-browse photo uploader.
 * Calls onFileSelected(File) when a valid image is chosen.
 */
export default function PhotoUpload({ onFileSelected, disabled }) {
  const inputRef  = useRef(null)
  const [dragging, setDragging] = useState(false)

  const handleFile = useCallback((file) => {
    if (!file) return
    if (!file.type.startsWith('image/')) {
      alert('Please select an image file (JPG, PNG, etc.)')
      return
    }
    onFileSelected(file)
  }, [onFileSelected])

  const onInputChange = (e) => handleFile(e.target.files?.[0])

  const onDrop = (e) => {
    e.preventDefault()
    setDragging(false)
    handleFile(e.dataTransfer.files?.[0])
  }

  return (
    <div
      className={`upload-zone ${dragging ? 'upload-zone--drag' : ''} ${disabled ? 'upload-zone--disabled' : ''}`}
      onClick={() => !disabled && inputRef.current?.click()}
      onDragOver={(e) => { e.preventDefault(); if (!disabled) setDragging(true) }}
      onDragLeave={() => setDragging(false)}
      onDrop={!disabled ? onDrop : undefined}
      role="button"
      tabIndex={disabled ? -1 : 0}
      aria-label="Upload crop photo"
      onKeyDown={(e) => e.key === 'Enter' && !disabled && inputRef.current?.click()}
    >
      <input
        ref={inputRef}
        type="file"
        accept="image/*"
        capture="environment"
        onChange={onInputChange}
        className="sr-only"
        disabled={disabled}
        aria-hidden="true"
      />
      <span className="upload-icon" aria-hidden="true">📷</span>
      <p className="upload-primary">Tap to take a photo or upload</p>
      <p className="upload-secondary">JPG, PNG — max 10 MB</p>
    </div>
  )
}

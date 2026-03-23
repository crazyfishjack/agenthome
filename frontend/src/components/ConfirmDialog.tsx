import React from 'react'

interface ConfirmDialogProps {
  isOpen: boolean
  title?: string
  message: string
  confirmText?: string
  cancelText?: string
  onConfirm: () => void
  onCancel: () => void
  type?: 'danger' | 'warning' | 'info'
}

export default function ConfirmDialog({
  isOpen,
  title,
  message,
  confirmText = '确定',
  cancelText = '取消',
  onConfirm,
  onCancel,
  type = 'danger'
}: ConfirmDialogProps) {
  if (!isOpen) return null

  const handleConfirm = (e: React.MouseEvent) => {
    e.stopPropagation()
    onConfirm()
  }

  const handleCancel = (e: React.MouseEvent) => {
    e.stopPropagation()
    onCancel()
  }

  const handleBackdropClick = (e: React.MouseEvent) => {
    e.stopPropagation()
    onCancel()
  }

  const getConfirmButtonClass = () => {
    switch (type) {
      case 'danger':
        return 'bg-danger-500 hover:bg-danger-600'
      case 'warning':
        return 'bg-warning-500 hover:bg-warning-600'
      case 'info':
        return 'bg-primary-500 hover:bg-primary-600'
      default:
        return 'bg-danger-500 hover:bg-danger-600'
    }
  }

  return (
    <div
      className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4"
      onClick={handleBackdropClick}
    >
      <div
        className="bg-white rounded-lg shadow-xl w-full max-w-md p-6"
        onClick={(e) => e.stopPropagation()}
      >
        {title && (
          <h3 className="text-lg font-semibold text-gray-800 mb-3">{title}</h3>
        )}
        <p className="text-sm text-gray-700 mb-6">{message}</p>
        <div className="flex items-center justify-end gap-3">
          <button
            onClick={handleCancel}
            className="px-4 py-2 text-sm text-gray-600 hover:bg-gray-100 rounded-full transition-colors"
          >
            {cancelText}
          </button>
          <button
            onClick={handleConfirm}
            className={`px-4 py-2 text-sm text-white ${getConfirmButtonClass()} rounded-full transition-colors`}
          >
            {confirmText}
          </button>
        </div>
      </div>
    </div>
  )
}

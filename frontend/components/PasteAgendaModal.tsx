'use client';

import React, { useState, useEffect, useRef } from 'react';
import { parseAgendaText, AgendaItem } from '@/lib/agendaApi';

interface PasteAgendaModalProps {
  isOpen: boolean;
  onClose: () => void;
  onItemsParsed: (items: AgendaItem[]) => void;
  idToken?: string;
}

export const PasteAgendaModal: React.FC<PasteAgendaModalProps> = ({
  isOpen,
  onClose,
  onItemsParsed,
  idToken = '',
}) => {
  const [text, setText] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (isOpen) {
      setTimeout(() => {
        textareaRef.current?.focus();
      }, 50);
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const handleParse = async (e: React.MouseEvent<HTMLButtonElement>) => {
    e.preventDefault();
    e.stopPropagation();

    if (!text.trim()) return;

    setLoading(true);
    setError(null);

    try {
      const data = await parseAgendaText(text, idToken);
      if (data && data.items) {
        onItemsParsed(data.items);
        setText('');
        onClose();
      } else {
        setError('Не вдалося отримати пункти порядку денного від сервера.');
      }
    } catch (err: unknown) {
      const errorMessage =
        err instanceof Error ? err.message : 'Помилка під час обробки тексту';
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const handleClose = (e: React.MouseEvent<HTMLButtonElement>) => {
    e.preventDefault();
    e.stopPropagation();
    onClose();
  };

  return (
    <div
      className="fixed inset-0 z-[9999] flex items-center justify-center bg-black/60 p-4 pointer-events-auto"
      onClick={(e) => e.stopPropagation()}
    >
      <div
        className="relative z-[10000] w-full max-w-lg rounded-lg bg-white p-6 shadow-2xl pointer-events-auto"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 className="mb-4 text-xl font-bold text-gray-900">
          Paste an Agenda (Bedrock AI)
        </h2>

        {error && (
          <div className="mb-4 rounded bg-red-100 p-3 text-sm text-red-700">
            {error}
          </div>
        )}

        <textarea
          ref={textareaRef}
          className="h-40 w-full rounded border border-gray-300 bg-white p-3 text-sm text-gray-900 placeholder-gray-400 focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 pointer-events-auto cursor-text"
          placeholder="Paste meeting text or raw agenda here..."
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => e.stopPropagation()}
          disabled={loading}
        />

        <div className="mt-4 flex justify-end gap-3">
          <button
            type="button"
            onClick={handleClose}
            disabled={loading}
            className="rounded px-4 py-2 text-sm text-gray-600 hover:bg-gray-100"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handleParse}
            disabled={loading || !text.trim()}
            className="rounded bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
          >
            {loading ? 'Processing with Bedrock...' : 'Parse Agenda'}
          </button>
        </div>
      </div>
    </div>
  );
};

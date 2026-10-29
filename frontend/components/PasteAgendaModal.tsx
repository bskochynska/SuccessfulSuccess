'use client';

import React, { useState } from 'react';
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
      className="fixed inset-0 z-[100] flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm"
      onClick={(e) => e.stopPropagation()}
    >
      <div
        className="w-full max-w-lg rounded-lg bg-white p-6 shadow-2xl dark:bg-gray-800"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 className="mb-4 text-xl font-bold text-gray-900 dark:text-white">
          Paste an Agenda (Bedrock AI)
        </h2>

        {error && (
          <div className="mb-4 rounded bg-red-100 p-3 text-sm text-red-700 dark:bg-red-900/30 dark:text-red-400">
            {error}
          </div>
        )}

        <textarea
          className="h-40 w-full rounded border border-gray-300 p-3 text-sm text-gray-900 focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
          placeholder="Paste meeting text or raw agenda here..."
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => e.stopPropagation()}
          disabled={loading}
          autoFocus
        />

        <div className="mt-4 flex justify-end gap-3">
          <button
            type="button"
            onClick={handleClose}
            disabled={loading}
            className="rounded px-4 py-2 text-sm text-gray-600 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-700"
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

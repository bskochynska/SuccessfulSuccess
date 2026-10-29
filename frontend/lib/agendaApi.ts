export interface AgendaItem {
  time_start?: string;
  time_end?: string;
  title: string;
  description?: string;
  assignee?: string;
  duration_minutes?: number;
}

export interface ParseAgendaResponse {
  items: AgendaItem[];
  summary?: string;
  raw_response?: string;
}

export async function parseAgendaText(
  agendaText: string,
  idToken: string
): Promise<ParseAgendaResponse> {
  const lambdaUrl = process.env.NEXT_PUBLIC_LAMBDA_AGENDA_URL;

  if (!lambdaUrl) {
    throw new Error('NEXT_PUBLIC_LAMBDA_AGENDA_URL is not configured');
  }

  const response = await fetch(lambdaUrl, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${idToken}`,
    },
    body: JSON.stringify({ agenda_text: agendaText }),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(
      errorData.detail || errorData.error || `Error ${response.status}: Failed to parse agenda`
    );
  }

  const rawData = await response.json();

  // Безпечно витягаємо items з верхнього рівня або з вкладеного об'єкта agenda
  const items = rawData.items || rawData.agenda?.items || [];
  const summary = rawData.summary || rawData.agenda?.summary;

  return {
    items,
    summary,
    raw_response: JSON.stringify(rawData),
  };
}

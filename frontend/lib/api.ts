/* Typed client for the FastAPI backend (see REAL-SPEC.md API contract).
 * NEXT_PUBLIC_API_URL is baked in at build time; it defaults to the local
 * backend so `npm run dev` works with no extra configuration.
 * All data fetching is client-side (the build is a static export). */

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export const TOKEN_KEY = "bowers_token";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string | null) {
  if (typeof window === "undefined") return;
  if (token) window.localStorage.setItem(TOKEN_KEY, token);
  else window.localStorage.removeItem(TOKEN_KEY);
  window.dispatchEvent(new Event("bowers-auth-changed"));
}

export interface User {
  id: number;
  name: string;
  email: string;
  role: string;
}

export interface AuthResponse {
  token: string;
  user: User;
}

export interface Resource {
  id: number;
  title: string;
  description: string;
  category: string;
  audience: string;
  link: string;
}

export interface Conference {
  id: number;
  name: string;
  date: string | null;
  end_date: string | null;
  location: string | null;
  status: "upcoming" | "past" | "cancelled" | "tba";
  description: string | null;
  link: string | null;
  attendees: number | null;
}

export interface CenterEvent {
  id: number;
  name: string;
  description: string | null;
  date: string | null;
  status: string | null;
  category: "program" | "conference" | "workshop" | "community" | string;
  location: string | null;
}

export interface NewsletterSignupResponse {
  ok: boolean;
  already_subscribed?: boolean;
  confirmation_token?: string;
  confirmation_url?: string;
}

export interface Appointment {
  id: number;
  name: string;
  email: string;
  topic: string;
  preferred_date: string | null;
  preferred_time: string | null;
  notes: string | null;
  status: string;
}

export interface OutreachEntry {
  id: number;
  date: string;
  program: string;
  contacts_reached: number;
  notes: string;
}

export interface DashboardData {
  totals: {
    subscribers: number;
    confirmed_subscribers: number;
    appointments_pending: number;
    resources: number;
    conferences: number;
    events: number;
    participation_total: number;
    outreach_contacts: number;
  };
  participation_by_conference: { conference: string; count: number }[];
  outreach_by_month: { month: string; contacts: number; entries: number }[];
  subscribers_by_month: { month: string; count: number }[];
  appointments_by_status: {
    pending: number;
    confirmed: number;
    declined: number;
    completed: number;
  };
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  const token = getToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;
  const res = await fetch(`${API_BASE}${path}`, { headers, ...init });
  if (!res.ok) {
    throw new Error(`API ${res.status}: ${await res.text()}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  health: () => request<{ status: string }>(`/api/health`),
  register: (body: { name: string; email: string; password: string }) =>
    request<AuthResponse>(`/api/auth/register`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  login: (body: { email: string; password: string }) =>
    request<AuthResponse>(`/api/auth/login`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  me: () => request<User>(`/api/auth/me`),
  resources: (params?: {
    search?: string;
    category?: string;
    audience?: string;
  }) => {
    const q = new URLSearchParams();
    if (params?.search) q.set("search", params.search);
    if (params?.category) q.set("category", params.category);
    if (params?.audience) q.set("audience", params.audience);
    const suffix = q.toString() ? `?${q.toString()}` : "";
    return request<Resource[]>(`/api/resources${suffix}`);
  },
  resource: (id: number) => request<Resource>(`/api/resources/${id}`),
  addResource: (body: {
    title: string;
    description: string;
    category: string;
    audience: string;
    link: string;
  }) =>
    request<Resource>(`/api/resources`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  conferences: () => request<Conference[]>(`/api/conferences`),
  events: () => request<CenterEvent[]>(`/api/events`),
  newsletterSignup: (body: {
    name: string;
    email: string;
    interests: string[];
    topics: string[];
    source: string;
  }) =>
    request<NewsletterSignupResponse>(`/api/newsletter/signup`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  newsletterConfirm: (token: string) =>
    request<{ ok: boolean; email: string }>(
      `/api/newsletter/confirm?token=${encodeURIComponent(token)}`
    ),
  newsletterUnsubscribe: (email: string) =>
    request<{ ok: boolean }>(`/api/newsletter/unsubscribe`, {
      method: "POST",
      body: JSON.stringify({ email }),
    }),
  requestAppointment: (body: {
    name: string;
    email: string;
    topic: string;
    preferred_date?: string;
    preferred_time?: string;
    notes?: string;
  }) =>
    request<{ id: number; status: string }>(`/api/appointments`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  appointments: () => request<Appointment[]>(`/api/appointments`),
  updateAppointment: (id: number, status: string) =>
    request<Appointment>(`/api/appointments/${id}`, {
      method: "PATCH",
      body: JSON.stringify({ status }),
    }),
  outreachList: () => request<OutreachEntry[]>(`/api/outreach`),
  addOutreach: (body: {
    date: string;
    program: string;
    contacts_reached: number;
    notes: string;
  }) =>
    request<OutreachEntry>(`/api/outreach`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  dashboard: () => request<DashboardData>(`/api/dashboard`),
  reportsSummary: () => request<Record<string, unknown>>(`/api/reports/summary`),
};

/* Real categories from the Bowers Belonging at Bowers resources pages
 * (REAL-SPEC.md §7.1). */
export const RESOURCE_CATEGORIES = [
  "Office services",
  "Community resources",
  "Campus partners",
];

export function formatDateRange(
  start: string | null,
  end: string | null
): string {
  if (!start && !end) return "Date to be announced";
  if (start && end && start !== end) return `${start} – ${end}`;
  return start ?? end ?? "";
}

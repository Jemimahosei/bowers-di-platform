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
  // Single opt-in: signup subscribes immediately. email_sent says
  // whether the welcome note went out — the subscription stands
  // either way.
  email_sent?: boolean;
  email_configured?: boolean;
}

export interface Slot {
  id: number;
  date: string;
  start_time: string;
  end_time: string;
  type: "call" | "in-person";
  host: string;
  status: "open" | "booked";
}

export interface Booking {
  id: number;
  slot_id: number;
  name: string;
  email: string;
  purpose: string;
  status: "booked" | "cancelled";
  slot?: Slot | null;
}

export interface Audience {
  id: number;
  name: string;
  source_org: string;
  description: string;
  contact_count: number;
  opted_out_count: number;
}

export interface Contact {
  id: number;
  audience_id: number;
  name: string;
  email: string;
  source_org: string;
  interests: string[];
  tags: string[];
  source: string;
  opted_out: boolean;
}

export interface AudienceDetail extends Audience {
  contacts: Contact[];
}

export interface OrgSubmission {
  id: number;
  org_name: string;
  rep_name: string;
  rep_email: string;
  notes: string;
  contacts: { name: string; email: string; interests: string[] }[];
  status: "pending" | "approved" | "rejected";
  audience_id?: number;
  contacts_added?: number;
}

export interface CampaignRecipient {
  email: string;
  name: string;
  source: string;
  status?: string;
  error?: string;
}

export interface Campaign {
  id: number;
  subject: string;
  body: string;
  sender_name: string;
  // Resources from the platform's real resource list featured in this
  // newsletter issue (ids, in display order) + the resolved rows.
  resource_ids: number[];
  featured_resources?: Resource[];
  audience_ids: number[];
  org_filter: string;
  interest_filter: string;
  include_self_signup: boolean;
  status: "draft" | "queued" | "sent" | "partially_sent";
  recipient_count: number;
  recipients?: CampaignRecipient[];
  email_configured?: boolean;
  message?: string;
  sent?: number;
  failed?: number;
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
    audiences: number;
    contacts: number;
    opted_out_contacts: number;
    campaigns: number;
    campaigns_sent: number;
    open_slots: number;
    upcoming_bookings: number;
    resources: number;
    conferences: number;
    events: number;
    participation_total: number;
    outreach_contacts: number;
  };
  participation_by_conference: { conference: string; count: number }[];
  outreach_by_month: { month: string; contacts: number; entries: number }[];
  subscribers_by_month: { month: string; count: number }[];
  bookings_by_status: { booked: number; cancelled: number };
  slots_by_status: { open: number; booked: number };
  campaigns_by_status: {
    draft: number;
    queued: number;
    sent: number;
    partially_sent: number;
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
  newsletterUnsubscribe: (email: string) =>
    request<{ ok: boolean }>(`/api/newsletter/unsubscribe`, {
      method: "POST",
      body: JSON.stringify({ email }),
    }),
  // ---- Slots & bookings (real booking with Dr. Roberts) ----
  slots: (openOnly = true) =>
    request<Slot[]>(`/api/slots?open_only=${openOnly ? "true" : "false"}`),
  createSlot: (body: {
    date: string;
    start_time: string;
    end_time: string;
    type: string;
    host?: string;
  }) =>
    request<Slot>(`/api/slots`, { method: "POST", body: JSON.stringify(body) }),
  deleteSlot: (id: number) =>
    request<{ ok: boolean }>(`/api/slots/${id}`, { method: "DELETE" }),
  bookSlot: (id: number, body: { name: string; email: string; purpose: string }) =>
    request<Booking>(`/api/slots/${id}/book`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  bookings: () => request<Booking[]>(`/api/bookings`),
  cancelBooking: (id: number) =>
    request<Booking>(`/api/bookings/${id}/cancel`, { method: "POST" }),

  // ---- Audiences & contacts (Core 1: who to reach) ----
  audiences: () => request<Audience[]>(`/api/audiences`),
  audience: (id: number) => request<AudienceDetail>(`/api/audiences/${id}`),
  createAudience: (body: { name: string; source_org: string; description: string }) =>
    request<Audience>(`/api/audiences`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  addContact: (
    audienceId: number,
    body: { name: string; email: string; source_org?: string; interests?: string[]; tags?: string[] }
  ) =>
    request<Contact>(`/api/audiences/${audienceId}/contacts`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  updateContact: (
    audienceId: number,
    contactId: number,
    body: { name?: string; interests?: string[]; tags?: string[]; opted_out?: boolean }
  ) =>
    request<Contact>(`/api/audiences/${audienceId}/contacts/${contactId}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),
  deleteContact: (audienceId: number, contactId: number) =>
    request<{ ok: boolean }>(
      `/api/audiences/${audienceId}/contacts/${contactId}`,
      { method: "DELETE" }
    ),
  contactsTemplate: async (): Promise<string> => {
    const token = getToken();
    const res = await fetch(`${API_BASE}/api/audiences/contacts/template`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
    if (!res.ok) throw new Error(`API ${res.status}`);
    return res.text();
  },
  uploadContacts: async (
    audienceId: number,
    file: File,
    preview: boolean
  ): Promise<{
    preview: boolean;
    valid_rows?: number;
    invalid_rows?: number;
    imported?: number;
    skipped?: number;
    errors: { row: number | null; reason: string }[];
    sample?: { name: string; email: string; interests: string[] }[];
  }> => {
    const token = getToken();
    const form = new FormData();
    form.append("file", file);
    form.append("preview", preview ? "true" : "false");
    const res = await fetch(
      `${API_BASE}/api/audiences/${audienceId}/contacts/upload`,
      {
        method: "POST",
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        body: form,
      }
    );
    if (!res.ok) throw new Error(`API ${res.status}: ${await res.text()}`);
    return res.json();
  },

  // ---- Org-rep submissions ----
  orgSubmissions: () => request<OrgSubmission[]>(`/api/org-submissions`),
  submitOrgContacts: (body: {
    org_name: string;
    rep_name: string;
    rep_email: string;
    notes?: string;
    contacts: { name: string; email: string; interests: string[] }[];
  }) =>
    request<OrgSubmission>(`/api/org-submissions`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  submitOrgContactsFile: async (
    body: { org_name: string; rep_name: string; rep_email: string; notes?: string },
    file: File
  ): Promise<OrgSubmission> => {
    const form = new FormData();
    form.append("org_name", body.org_name);
    form.append("rep_name", body.rep_name);
    form.append("rep_email", body.rep_email);
    form.append("notes", body.notes ?? "");
    form.append("contacts_file", file);
    const res = await fetch(`${API_BASE}/api/org-submissions`, {
      method: "POST",
      body: form,
    });
    if (!res.ok) throw new Error(`API ${res.status}: ${await res.text()}`);
    return res.json();
  },
  reviewOrgSubmission: (id: number, body: { decision: string; audience_id?: number }) =>
    request<OrgSubmission>(`/api/org-submissions/${id}/review`, {
      method: "POST",
      body: JSON.stringify(body),
    }),

  // ---- Campaigns (Core 2: email the people it reaches) ----
  campaigns: () => request<Campaign[]>(`/api/campaigns`),
  campaign: (id: number) => request<Campaign>(`/api/campaigns/${id}`),
  createCampaign: (body: {
    subject: string;
    body: string;
    sender_name: string;
    resource_ids?: number[];
    audience_ids: number[];
    org_filter?: string;
    interest_filter?: string;
    include_self_signup?: boolean;
  }) =>
    request<Campaign>(`/api/campaigns`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  updateCampaign: (
    id: number,
    body: {
      subject?: string;
      body?: string;
      sender_name?: string;
      resource_ids?: number[];
      audience_ids?: number[];
      org_filter?: string;
      interest_filter?: string;
      include_self_signup?: boolean;
    }
  ) =>
    request<Campaign>(`/api/campaigns/${id}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),
  sendCampaign: (id: number) =>
    request<Campaign>(`/api/campaigns/${id}/send`, { method: "POST" }),
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

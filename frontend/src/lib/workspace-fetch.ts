/** Carry the selected organization consistently through native API requests. */
export function workspaceFetch(input: RequestInfo | URL, init?: RequestInit): Promise<Response> {
  if (typeof window !== 'undefined' && typeof input === 'string' && /^\/api\/v[12]\//.test(input)) {
    const workspaceId = Number(localStorage.getItem('current_workspace_id'));
    if (Number.isSafeInteger(workspaceId) && workspaceId > 0) {
      const url = new URL(input, window.location.origin);
      if (!url.searchParams.has('workspace_id')) url.searchParams.set('workspace_id', String(workspaceId));
      return fetch(`${url.pathname}${url.search}`, init);
    }
  }
  return fetch(input, init);
}

import type { User } from './types';

export function loginDestination(user: User | null) {
  if (user?.must_change_password || user?.security_setup_pending) return '/account/setup';
  if (user?.is_collaborator) return '/account/workspaces';
  return user?.is_superuser ? '/admin' : '/account/entry';
}

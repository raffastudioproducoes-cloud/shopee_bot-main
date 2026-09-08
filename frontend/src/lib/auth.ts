/**
 * Funções de autenticação para a API Python (FastAPI)
 */

export async function login(username: string, password: string): Promise<{ msg: string }> {
  const response = await fetch('/api/auth/login', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
    },
    body: new URLSearchParams({
      username: username,
      password: password,
    }),
    credentials: 'include',
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Erro desconhecido' }));
    throw new Error(error.detail || 'Erro ao fazer login');
  }

  return response.json();
}

export async function logout(): Promise<{ msg: string }> {
  const response = await fetch('/api/auth/logout', {
    method: 'POST',
    credentials: 'include',
  });

  if (!response.ok) {
    throw new Error('Erro ao fazer logout');
  }

  return response.json();
}

export async function getMe(): Promise<{
  id: string;
  username: string;
  access: string;
} | null> {
  const response = await fetch('/api/auth/me', {
    method: 'GET',
    credentials: 'include',
  });

  if (response.status === 401) {
    return null;
  }

  if (!response.ok) {
    throw new Error('Erro ao buscar perfil');
  }

  return response.json();
}

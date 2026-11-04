-- Schema canônico de identidade. Dono: SAGA.
-- Os subsistemas NUNCA criam nem alteram tabelas neste schema — apenas leem.
-- Convenção: saga/db/schema.sql é a fonte da verdade de `auth.*`.
--
-- Aplicar: docker compose -f compose.dev.yml run --rm schema

CREATE SCHEMA IF NOT EXISTS auth;

CREATE TABLE IF NOT EXISTS auth.users (
  id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  login             text NOT NULL UNIQUE,
  name              text,
  email             text,
  role_base         text NOT NULL DEFAULT 'UNDEFINIDO'
                    CHECK (role_base IN ('ALUNO', 'PROFESSOR', 'UNDEFINIDO')),
  profile_complete  boolean NOT NULL DEFAULT false,
  status            text NOT NULL DEFAULT 'ATIVO'
                    CHECK (status IN ('ATIVO', 'INATIVO')),
  created_at        timestamptz NOT NULL DEFAULT now(),
  last_login_at     timestamptz
);

CREATE INDEX IF NOT EXISTS idx_auth_users_login ON auth.users (login);

-- Campos de papel como COLUNAS (uma linha por usuário).
-- Quais colunas se aplicam a cada papel é validado em código: Postgres não
-- expressa CHECK que cruza tabelas.
CREATE TABLE IF NOT EXISTS auth.user_profiles (
  user_id        uuid PRIMARY KEY REFERENCES auth.users (id) ON DELETE CASCADE,
  matricula      text UNIQUE,
  curso          text,        -- só ALUNO
  programa_pos   text,        -- só ALUNO
  departamento   text,        -- só PROFESSOR
  data_matricula date         -- só ALUNO
);

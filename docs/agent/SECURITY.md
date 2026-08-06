# Segurança — Monitor Comunitário

## Classificação

- Dados pessoais: nome, telefone/WhatsApp, município, bairro, rua, número, CEP e preferências de alerta.
- Fonte externa pública: página pública de avisos de desligamentos da Celesc.
- Integrações externas potenciais: Evolution API/WhatsApp, Supabase/Postgres, analytics/ads quando habilitados.
- Admin: rotas protegidas por sessão HttpOnly e token CSRF.

## Princípios

- Coletar o mínimo necessário.
- Usar linguagem de possibilidade: alertas podem indicar impacto, não garantia.
- A fonte oficial continua sendo a Celesc.
- Não acessar dados privados da Celesc, titularidade, CPF, CNPJ, faturas, Agência Web ou credenciais de usuários.
- Não enviar WhatsApp sem consentimento e configuração explícita.
- Não expor telefone/endereço em logs, screenshots, issues, PRs ou exemplos.

## Segredos

Nunca registrar em Markdown, issue, PR, logs ou memória:

```text
ADMIN_API_KEY
DATABASE_URL real
EVOLUTION_API_KEY
EVOLUTION_INSTANCE
tokens GitHub/Notion
senhas
webhook secrets
```

Use placeholders:

```text
<ADMIN_API_KEY>
<DATABASE_URL>
<EVOLUTION_API_KEY>
```

## Ações bloqueadas sem aprovação explícita

- Deploy em produção ou ambiente público.
- Migração destrutiva.
- Remoção de cadastros, notificações, snapshots ou logs.
- Ativação de envio real por WhatsApp/Evolution.
- Alteração de DNS, Traefik, proxy ou certificados.
- Mudança de política de retenção/exclusão de dados.
- Exposição pública de dados operacionais.

## Deploy/produção

Produção exige:

1. mudança revisada;
2. testes e build aprovados;
3. commit/versão identificável;
4. backup quando houver dados/migração;
5. plano de rollback;
6. autorização humana;
7. verificação pós-deploy;
8. registro do resultado.

## Incidente

Em caso de possível exposição de segredo ou dado pessoal:

1. parar propagação;
2. preservar evidências sem repetir o segredo/dado;
3. avisar Frank;
4. revogar/rotacionar credenciais quando aplicável;
5. registrar impacto e correção sem expor valores sensíveis.

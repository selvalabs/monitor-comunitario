# Product Copy Guidelines

Issue: #130  
Status: approved direction, awaiting copy-map review  
Scope: Portuguese product copy for the Monitor Comunitario.

## Goal

Make the product easy to understand on a first visit. A resident should know what
the service does, what it does not do, what information is required, and what
happens next without reading technical explanations.

The Monitor Comunitario is an independent service that republishes and matches
public notices of planned Celesc outages. It does not predict outages, replace
Celesc, or guarantee delivery of a notice.

## Voice

The voice is calm, direct, local, and factual.

- Prefer short sentences and one action per sentence.
- Address the resident with "voce" and use active voice.
- Say "desligamento programado" when precision matters. Use "aviso" as the
  shorter companion term.
- Say "codigo de acesso", not "codigo privado".
- Say "area do morador", not "painel" for resident-facing navigation.
- State uncertainty plainly: notices can change or be cancelled by Celesc.
- Explain the next step immediately after an action.

Avoid implementation language in resident-facing copy:

- "cruzamento", "persistencia", "hash", "MVP", "scheduler", "matching";
- internal provider names or channel architecture;
- promises that every outage or notice will be delivered.

## Product terminology

| Use | Avoid | Reason |
| --- | --- | --- |
| Aviso de desligamento programado | Falta de energia | Preserves the service's actual scope. |
| Codigo de acesso | Codigo privado | Explains the purpose without sounding technical. |
| Confirmar cadastro | Ativar fluxo / validar usuario | Describes the resident's action. |
| Area do morador | Painel do morador | Keeps the destination familiar. |
| Avisos encontrados | Alertas ligados ao cadastro | Is shorter and more concrete. |
| Excluir cadastro e dados | Exclusao definitiva de entidade | Is plain and transparent. |

## Copy map

### Public page

| Location | Current intent | Proposed copy |
| --- | --- | --- |
| Brand subtitle | Describe product | `avisos de desligamentos programados` |
| Main heading | Explain benefit | `Saiba sobre desligamentos programados perto de voce.` |
| Main introduction | Explain two paths | `Cadastre seu endereco para receber avisos. Se ja tem cadastro, entre para consultar seus avisos.` |
| New registration card | Start registration | Label: `Novo cadastro`; title: `Cadastrar endereco`; body: `Informe seu endereco e confirme seu e-mail e WhatsApp.`; button: `Cadastrar endereco` |
| Existing registration card | Access account | Label: `Ja tenho cadastro`; title: `Ver meus avisos`; body: `Entre com seu telefone e codigo de acesso.`; button: `Entrar` |
| Independence notice | Set source boundary | `Este e um servico independente. Consulte a Celesc para informacoes oficiais e atualizadas.` |
| Three-step card 1 | Explain registration | Title: `Informe seu endereco`; body: `Pedimos apenas os dados necessarios para localizar sua regiao.` |
| Three-step card 2 | Explain confirmation | Title: `Confirme seus contatos`; body: `Confirme o e-mail e responda a mensagem enviada no WhatsApp.` |
| Three-step card 3 | Explain access | Title: `Acompanhe seus avisos`; body: `Use seu telefone e codigo de acesso para entrar quando quiser.` |
| Registration heading | Start form | `Cadastre seu endereco` |
| Registration introduction | Explain form | `Informe os dados do local onde voce quer receber avisos.` |
| Municipality-wide option | Explain fallback matching | `Tambem quero receber avisos gerais do municipio quando o endereco do aviso nao estiver detalhado.` |
| Submit | Register | `Continuar` |
| Email confirmation heading | Explain verification | `Confirme seu e-mail` |
| Email confirmation instruction | Explain OTP | `Digite o codigo enviado para seu e-mail. Ele vale por 48 horas.` |
| Email confirmation action | Submit OTP | `Confirmar e-mail` |
| Access-code heading | Explain credential | `Guarde seu codigo de acesso` |
| Access-code body | Explain use | `Use este codigo com seu telefone para entrar na area do morador. Ele aparece apenas agora.` |
| Existing registration sidebar | Direct existing user | Title: `Ja se cadastrou?`; body: `Entre para ver seus dados e avisos.`; button: `Entrar na area do morador` |
| How it works | Explain service | Heading: `Como funciona`; steps: `Buscamos avisos publicos`, `Localizamos sua regiao`, `Mostramos os avisos na sua area` |
| Footer | Product identity | `Monitor Comunitario: avisos publicos de desligamentos programados.` |

### Confirmation flow

| Channel | Moment | Proposed copy |
| --- | --- | --- |
| Browser | Registration submitted | `Enviamos um codigo para seu e-mail. Confirme-o para continuar.` |
| Email subject | OTP sent | `Confirme seu cadastro no Monitor Comunitario` |
| Email body | OTP sent | `Use este codigo para confirmar seu e-mail: {otp}. Ele vale por 48 horas. Se voce nao iniciou este cadastro, ignore esta mensagem.` |
| Browser | Email confirmed | `E-mail confirmado. Agora responda a mensagem enviada no WhatsApp para concluir o cadastro.` |
| WhatsApp | Phone confirmation | `Oi, {name}. Voce quer receber avisos de desligamentos programados para o endereco cadastrado? Responda OK para confirmar ou CANCELAR para encerrar o cadastro. Esta confirmacao vale por 48 horas.` |
| WhatsApp | Confirmation complete | `Cadastro confirmado. Guarde seu codigo de acesso: {access_code}. Entre na area do morador para ver seus avisos: {url}` |
| WhatsApp | Expired or cancelled | `O cadastro nao foi confirmado e foi encerrado. Para tentar novamente, faca um novo cadastro no site.` |

### Member area

| Location | Proposed copy |
| --- | --- |
| Heading | `Seus avisos` |
| Introduction | `Entre com o telefone cadastrado e seu codigo de acesso.` |
| Access-code help | `Voce recebeu este codigo ao confirmar o cadastro.` |
| Access action | `Entrar` |
| Session clear action | `Sair desta sessao` |
| Registration details heading | `Seu endereco` |
| Alerts heading | `Avisos para voce` |
| Empty state | `Nao encontramos avisos para seu endereco.` |
| Celesc source disclosure | `Ver aviso original da Celesc` |
| Delete section heading | `Excluir meus dados` |
| Delete section body | `Isso apaga seu cadastro, endereco e historico de avisos.` |
| Delete confirmation | `Entendo que esta acao nao pode ser desfeita.` |
| Delete action | `Excluir cadastro e dados` |

### Admin

Admin copy must remain compact and operational. It may use technical terms when
they help the operator act, but should avoid internal names that do not affect a
decision.

| Current pattern | Proposed pattern |
| --- | --- |
| `Painel de diagnostico` | `Visao da operacao` |
| Long operational summary | `Acompanhe a coleta, os avisos e os cadastros pendentes.` |
| `Rodar coleta manual` | `Executar coleta agora` |
| `Numeros cadastrados` | `Cadastros pendentes` |
| `Aprove apenas numeros de teste...` | `Libere apenas cadastros confirmados.` |
| `Matches criados` | `Enderecos correspondentes` |
| `Scheduler` | `Proxima coleta` when the schedule is shown; keep `Scheduler` only if it is a health status. |

### Privacy, terms, and consent

Legal pages keep their legal meaning and do not become marketing copy. The public
summary and consent dialog should be plain:

| Location | Proposed copy |
| --- | --- |
| Consent heading | `Sua privacidade` |
| Consent intro | `Usamos o necessario para manter seu cadastro e suas preferencias. Publicidade e analises sao opcionais.` |
| Required category | `Necessarios para o funcionamento do site` |
| Analytics category | `Analises para melhorar o servico` |
| Ads category | `Publicidade` |
| Reject action | `Usar apenas o necessario` |
| Accept action | `Aceitar opcionais` |
| Settings action | `Escolher preferencias` |

## Dynamic messages

The same voice must apply to browser status messages and API-provided messages.
Error text should say what happened and the next useful action without revealing
implementation details.

| Situation | Proposed copy |
| --- | --- |
| Required data missing | `Preencha os campos obrigatorios para continuar.` |
| Invalid email | `Informe um e-mail valido.` |
| Email delivery failed | `Nao foi possivel enviar o e-mail agora. Tente novamente em alguns minutos.` |
| Invalid or expired OTP | `Esse codigo nao e valido ou expirou. Solicite um novo cadastro.` |
| Invalid access | `Nao encontramos um cadastro com esses dados.` |
| Session cleared | `Voce saiu desta sessao.` |
| Deletion completed | `Seu cadastro e seus dados foram excluidos.` |
| Generic failure | `Nao foi possivel concluir agora. Tente novamente em alguns minutos.` |

## Implementation boundaries

This editorial pass changes visible Portuguese copy only. It does not change:

- routes, field names, API contracts, event types, schemas, or persistence;
- authentication and confirmation behavior;
- legal obligations or the source-of-truth role of Celesc;
- non-Portuguese translations without a corresponding reviewed translation pass;
- advertising or analytics activation.

## Validation

1. Review each resident-facing flow from registration through member access.
2. Confirm messages describe the existing 48-hour confirmation windows.
3. Verify that no copy claims an unimplemented delivery guarantee.
4. Preserve legal meaning in terms, privacy, and consent content.
5. Run the existing web and API tests after implementation.


# LGPD, privacidade e cookies

## Escopo desta etapa

Esta etapa adiciona transparência e controle técnico para o usuário final:

```text
/privacidade
/termos
/cookies
/public/config
checkbox obrigatório no cadastro
consent manager
bloqueio de ads/analytics por flag e consentimento
```

## Dados pessoais tratados

O cadastro pode coletar:

```text
nome
telefone/WhatsApp
município
bairro
rua
número
CEP
preferência de alerta amplo do município
```

## Ads e analytics

O projeto foi preparado para dois modelos:

```text
pré-ads: sem script externo
ads: scripts carregados apenas após consentimento
```

## Produção real

Antes de disponibilizar o serviço publicamente, recomenda-se revisar:

```text
controlador dos dados
canal de contato
base legal
retenção
exclusão
backup
segurança
operadores/suboperadores
provedores de ads
provedores de analytics
termos de integração com WhatsApp/Evolution API
```

Os textos adicionados são base técnica e informativa para portfólio, não substituem revisão jurídica.


## Exclusão pelo morador

A área do morador oferece exclusão permanente autenticada pelo telefone e código privado. A confirmação exige uma segunda etapa visual e o código é validado novamente no backend. A exclusão remove o cadastro e os registros derivados de alertas, matches e eventos relacionados.

A retenção automática de cadastros apenas desativados permanece fora desta etapa até que o prazo operacional seja definido.


## Cadastro verificado

O cadastro público permanece pendente no Redis até a confirmação do e-mail e do telefone. O OTP tem expiração e limite de tentativas. Após o e-mail, o sistema envia uma mensagem WhatsApp determinística; somente `OK` ativa o cadastro, `CANCELAR` remove o pendente e a ausência de resposta expira a solicitação.

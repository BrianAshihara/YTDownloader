# Assinatura de código (SignPath) e o aviso do Windows

## Por que o Windows bloqueia o instalador

São dois mecanismos diferentes:

| Aviso | Causa | Solução |
|---|---|---|
| **SmartScreen** ("O Windows protegeu o computador") | O arquivo **não é assinado** e não tem reputação de downloads | Assinatura de código + tempo/downloads para criar reputação |
| **Defender / antivírus** ("Trojan:Win32/Wacatac", etc.) | Falso positivo por heurística (bootloader do PyInstaller, UPX, onefile) | Já mitigado neste projeto: `onedir`, sem UPX, bootloader compilado no CI. Se acontecer, envie para https://www.microsoft.com/wdsi/filesubmission |

Não existe forma legítima de "desligar" o SmartScreen para os outros usuários.
O caminho correto é assinar o executável.

## SignPath Foundation (gratuito para open source)

1. Confira se o projeto cumpre os requisitos: https://signpath.org/terms
   (licença OSI como a MIT, repositório público, releases compiladas pelo CI,
   e uma política de assinatura publicada no README).
2. Faça o pedido em https://signpath.org/apply.
3. Depois da aprovação, no painel do SignPath:
   - Crie o projeto (ex.: `YTDownloader`) e conecte o repositório GitHub
     como *Trusted Build System*.
   - Crie duas **artifact configurations** com os slugs `app` e `installer`
     (conteúdo abaixo).
   - Anote a signing policy (normalmente `release-signing`).
4. No GitHub → *Settings → Secrets and variables → Actions*:
   - **Variables**: `SIGNPATH_ORGANIZATION_ID`, `SIGNPATH_PROJECT_SLUG`,
     `SIGNPATH_POLICY_SLUG`
   - **Secret**: `SIGNPATH_API_TOKEN`
5. Crie uma tag (`git tag v2.0.0 && git push origin v2.0.0`). O workflow
   `release.yml` assina o `YTDownloader.exe`, gera o instalador, assina o
   instalador e cria uma release **rascunho** para você revisar.

Enquanto as variáveis não existem, o workflow funciona normalmente, só que gera
os arquivos sem assinatura.

### Artifact configuration `app`

```xml
<?xml version="1.0" encoding="utf-8"?>
<artifact-configuration xmlns="http://signpath.io/artifact-configuration/v1">
  <zip-file>
    <pe-file path="YTDownloader.exe">
      <authenticode-sign />
    </pe-file>
  </zip-file>
</artifact-configuration>
```

### Artifact configuration `installer`

```xml
<?xml version="1.0" encoding="utf-8"?>
<artifact-configuration xmlns="http://signpath.io/artifact-configuration/v1">
  <zip-file>
    <pe-file path="YTDownloader-Setup.exe">
      <authenticode-sign />
    </pe-file>
  </zip-file>
</artifact-configuration>
```

> Só o código do projeto é assinado. `ffmpeg.exe` e `deno.exe` são de terceiros
> e não devem ser assinados com o certificado do projeto.

## Política de assinatura (texto para o README, exigido pelo SignPath)

> Free code signing provided by [SignPath.io](https://signpath.io), certificate
> by [SignPath Foundation](https://signpath.org). Releases are built and signed
> exclusively by GitHub Actions from this repository.

## Alternativas pagas

- **Certum Open Source Code Signing**: barato, aceita pessoa física.
- **Azure Artifact Signing** (antigo Trusted Signing): cerca de US$ 10/mês.
  Verifique se o seu país é aceito para pessoa física.
- Certificados OV/EV tradicionais: caros e exigem token físico ou HSM em nuvem.
  Desde 2024 o EV não dá mais reputação instantânea no SmartScreen.

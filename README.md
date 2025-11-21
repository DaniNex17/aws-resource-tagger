# AWS Resource Tagging - GitHub Actions

Pipeline automatizado para aplicar tags a recursos AWS de forma masiva usando GitHub Actions.

## 🚀 Características

- ✅ Etiquetado masivo de recursos AWS por ARN
- ✅ Soporte multi-cuenta con assume role
- ✅ Aprobación manual por ambiente
- ✅ Reportes detallados de éxito/fallo
- ✅ Procesamiento en lotes optimizado
- ✅ Detección automática de ambiente desde Parameter Store

## 📋 Requisitos

1. **Cuenta de GitHub** (gratuita)
2. **Credenciales AWS** con permisos de:
   - `tag:TagResources`
   - `tag:GetResources`
   - `sts:AssumeRole` (si usas multi-cuenta)
   - Permisos específicos por servicio (S3, Lambda, etc.)

## ⚙️ Configuración

### 1. Configurar Secrets en GitHub

Ve a tu repositorio → Settings → Secrets and variables → Actions → New repository secret

Agrega los siguientes secrets:

```
AWS_ACCESS_KEY_ID          # Tu Access Key ID
AWS_SECRET_ACCESS_KEY      # Tu Secret Access Key
```

**Opcional** (para multi-cuenta con assume role):
```
AWS_ROLE_ARN_PREFIX        # Ejemplo: arn:aws:iam::
AWS_ROLE_NAME              # Ejemplo: terraform
```

### 2. Configurar Environments (para aprobaciones)

Ve a Settings → Environments → New environment

Crea 3 ambientes:
- `dev` - Sin protección o aprobación opcional
- `qc` - Con 1 revisor requerido
- `pdn` - Con 2+ revisores requeridos

Para cada ambiente, configura:
1. Required reviewers: Agrega usuarios que deben aprobar
2. Wait timer: Opcional, tiempo de espera antes de ejecutar

## 🎯 Uso

### Ejecutar el Pipeline

1. Ve a la pestaña **Actions** en tu repositorio
2. Selecciona **AWS Resource Tagging**
3. Click en **Run workflow**
4. Completa los parámetros:

```yaml
resource_arns: arn:aws:lambda:us-east-1:123456789012:function:mi-funcion,arn:aws:s3:::mi-bucket
custom_tags: bia=true,owner=mi-equipo,project=demo
environment: dev
```

### Formato de ARNs

**ARN simple:**
```
arn:aws:lambda:us-east-1:123456789012:function:mi-funcion
```

**Múltiples ARNs (separados por coma):**
```
arn:aws:lambda:us-east-1:123456789012:function:func1,arn:aws:s3:::bucket1
```

**ARN con Account ID explícito (para recursos sin Account ID en el ARN):**
```
[arn:aws:s3:::mi-bucket,123456789012]
```

### Formato de Tags

```
clave1=valor1,clave2=valor2,clave3=valor3
```

Ejemplo:
```
bia=true,owner=equipo-data,env=pdn,project=analytics
```

## 🏗️ Arquitectura

```
┌─────────────────┐
│  GitHub Actions │
└────────┬────────┘
         │
         ├─► Validación de parámetros
         │
         ├─► Aprobación manual (según ambiente)
         │
         ├─► Configurar credenciales AWS
         │
         ├─► Agrupar recursos por cuenta
         │
         ├─► Para cada cuenta:
         │   ├─► Assume role (si aplica)
         │   ├─► Aplicar tags con boto3
         │   └─► Generar reporte
         │
         └─► Subir reportes como artifacts
```

## 📊 Servicios AWS Soportados

El script soporta todos los servicios compatibles con:
- **Resource Groups Tagging API** (mayoría de servicios)
- **APIs específicas** para:
  - S3 Buckets
  - AppConfig
  - Route53 Resolver

## 🔒 Seguridad

### Permisos Mínimos Requeridos

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "tag:TagResources",
        "tag:GetResources",
        "tag:GetTagKeys",
        "tag:GetTagValues"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:PutBucketTagging",
        "s3:GetBucketTagging"
      ],
      "Resource": "arn:aws:s3:::*"
    }
  ]
}
```

### Para Multi-Cuenta (Assume Role)

**En la cuenta principal:**
```json
{
  "Effect": "Allow",
  "Action": "sts:AssumeRole",
  "Resource": "arn:aws:iam::*:role/terraform"
}
```

**En cada cuenta destino (Trust Policy del rol):**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::CUENTA_PRINCIPAL:user/github-actions"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
```

## 📈 Reportes

Después de cada ejecución, se generan reportes descargables:
- `successful_arns.txt` - ARNs etiquetados exitosamente
- `failed_arns.txt` - ARNs que fallaron con detalles del error

Para descargarlos:
1. Ve a la ejecución del workflow
2. Scroll hasta **Artifacts**
3. Descarga `tagging-reports`

## 🆚 Diferencias con Azure DevOps

| Característica | Azure DevOps | GitHub Actions |
|---------------|--------------|----------------|
| Costo | Requiere organización | 2,000 min/mes gratis |
| Aprobaciones | Environments | Environments |
| Secrets | Service Connections | Repository Secrets |
| Runners | Pool específico | ubuntu-latest |
| Sintaxis | Azure Pipelines YAML | GitHub Actions YAML |

## 🐛 Troubleshooting

### Error: "No se pudo asumir rol"
- Verifica que el rol existe en la cuenta destino
- Confirma que la Trust Policy permite el assume role
- Revisa que los secrets `AWS_ROLE_ARN_PREFIX` y `AWS_ROLE_NAME` estén configurados

### Error: "AccessDenied"
- Verifica permisos de `tag:TagResources`
- Para S3, verifica `s3:PutBucketTagging`
- Confirma que el usuario/rol tiene acceso a los recursos

### Error: "InvalidParameterException"
- Verifica que los ARNs sean válidos
- Confirma el formato de los tags (clave=valor)

## 💡 Tips

1. **Prueba primero en dev**: Usa el ambiente `dev` para probar antes de producción
2. **Lotes pequeños**: Procesa grupos pequeños de recursos para facilitar debugging
3. **Revisa los logs**: Los logs de GitHub Actions son muy detallados
4. **Usa artifacts**: Descarga los reportes para análisis posterior

## 📝 Ejemplo Completo

```yaml
# Etiquetar 3 recursos en producción
resource_arns: |
  arn:aws:lambda:us-east-1:123456789012:function:api-handler,
  arn:aws:dynamodb:us-east-1:123456789012:table/users,
  [arn:aws:s3:::my-data-bucket,123456789012]

custom_tags: bia=true,owner=platform-team,env=pdn,cost-center=engineering

environment: pdn
```

## 🤝 Contribuir

1. Fork el repositorio
2. Crea una rama: `git checkout -b feature/mejora`
3. Commit: `git commit -am 'Agrega nueva funcionalidad'`
4. Push: `git push origin feature/mejora`
5. Abre un Pull Request

## 📄 Licencia

MIT License - Siéntete libre de usar y modificar

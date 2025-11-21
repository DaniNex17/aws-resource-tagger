# 🔒 Guía de Seguridad

## Opciones de Credenciales

Este proyecto ofrece 3 workflows con diferentes niveles de seguridad:

### 1. 🔐 Credenciales Temporales (MÁS SEGURO) ⭐ RECOMENDADO

**Archivo:** `.github/workflows/manual-credentials.yml`

**Ventajas:**
- ✅ Credenciales temporales (1 hora)
- ✅ No se guardan en GitHub
- ✅ Cero riesgo de exposición
- ✅ Ideal para SSO/AWS IAM Identity Center

**Cómo usar:**
1. Obtén credenciales temporales de tu portal SSO
2. Ve a Actions → "AWS Tagging (Credenciales Temporales)"
3. Pega las 3 credenciales en cada ejecución:
   - AWS Access Key ID
   - AWS Secret Access Key
   - AWS Session Token

**Ejemplo de credenciales temporales:**
```bash
# Desde tu portal SSO, copias algo como:
export AWS_ACCESS_KEY_ID="ASIA..."
export AWS_SECRET_ACCESS_KEY="wJalr..."
export AWS_SESSION_TOKEN="IQoJb3JpZ2luX2VjE..."
```

### 2. 🔑 Credenciales en Secrets (SEGURO)

**Archivo:** `.github/workflows/simple-tags.yml`

**Ventajas:**
- ✅ No ingresas credenciales cada vez
- ✅ Encriptadas en GitHub
- ✅ Bueno para automatización

**Desventajas:**
- ⚠️ Credenciales permanentes
- ⚠️ Requiere usuario IAM dedicado

**Cómo usar:**
1. Crea usuario IAM: `github-actions-tagger`
2. Guarda en Settings → Secrets:
   - `AWS_ACCESS_KEY_ID`
   - `AWS_SECRET_ACCESS_KEY`

### 3. 🏢 Multi-Cuenta con Assume Role (EMPRESARIAL)

**Archivo:** `.github/workflows/apply-tags.yml`

**Para:** Organizaciones con múltiples cuentas AWS

## 🎯 Recomendación por Caso de Uso

| Escenario | Workflow Recomendado |
|-----------|---------------------|
| Uso personal con SSO | `manual-credentials.yml` ⭐ |
| Automatización frecuente | `simple-tags.yml` |
| Múltiples cuentas AWS | `apply-tags.yml` |

## 🛡️ Mejores Prácticas

### Si Usas Credenciales Temporales (SSO)

1. ✅ Usa `manual-credentials.yml`
2. ✅ Copia las credenciales directamente del portal SSO
3. ✅ No las guardes en ningún lado
4. ✅ Expiran automáticamente en 1 hora

### Si Usas Credenciales Permanentes

1. ✅ Crea usuario IAM dedicado (no uses tu usuario personal)
2. ✅ Aplica permisos mínimos (solo tagging)
3. ✅ Rota las keys cada 3-6 meses
4. ✅ Habilita MFA en el usuario IAM
5. ✅ Monitorea el uso con CloudTrail

## 🔐 Permisos Mínimos Recomendados

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowResourceTagging",
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
      "Sid": "AllowS3Tagging",
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

## ⚠️ Qué NO Hacer

- ❌ NO pongas credenciales en el código
- ❌ NO uses tu usuario personal de AWS
- ❌ NO des permisos de administrador
- ❌ NO compartas las credenciales
- ❌ NO las guardes en archivos locales

## 🔍 Verificar Seguridad

### Revisar Logs de GitHub Actions

Los secrets se enmascaran automáticamente:
```
AWS_ACCESS_KEY_ID: ***
AWS_SECRET_ACCESS_KEY: ***
```

### Revisar Uso en AWS CloudTrail

Monitorea las acciones realizadas:
```bash
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=Username,AttributeValue=github-actions-tagger \
  --max-results 50
```

## 📞 Reportar Problemas de Seguridad

Si encuentras un problema de seguridad, por favor:
1. NO abras un issue público
2. Contacta al mantenedor directamente
3. Describe el problema en detalle

## 🔄 Rotación de Credenciales

### Para Credenciales Permanentes

Cada 3-6 meses:
1. Crea nuevas Access Keys en AWS IAM
2. Actualiza los Secrets en GitHub
3. Elimina las keys antiguas en AWS
4. Verifica que todo funcione

### Para Credenciales Temporales

No requiere rotación (expiran automáticamente) ✅

## 📚 Recursos Adicionales

- [AWS IAM Best Practices](https://docs.aws.amazon.com/IAM/latest/UserGuide/best-practices.html)
- [GitHub Secrets Documentation](https://docs.github.com/en/actions/security-guides/encrypted-secrets)
- [AWS Security Best Practices](https://aws.amazon.com/security/best-practices/)

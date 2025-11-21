#!/usr/bin/env python3
import json
import boto3
import sys
import argparse
import logging
from botocore.exceptions import ClientError

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def parse_tags(tags_string):
    """Convierte string de tags 'key1=value1,key2=value2' a diccionario"""
    if not tags_string:
        return {}
    
    tags = {}
    for tag_pair in tags_string.split(','):
        if '=' in tag_pair:
            key, value = tag_pair.split('=', 1)
            tags[key.strip()] = value.strip()
    return tags

def validate_arn(arn):
    """Valida que el ARN tenga el formato correcto"""
    # Validación simplificada - solo verificar que empiece con arn:aws:
    return arn.startswith('arn:aws:')

def get_service_from_arn(arn):
    """Extrae el servicio AWS del ARN"""
    try:
        return arn.split(':')[2]
    except IndexError:
        return None

def get_resource_type_from_arn(arn):
    """Extrae el tipo de recurso del ARN"""
    try:
        parts = arn.split(':')
        if len(parts) >= 6:
            resource_part = parts[5]
            if '/' in resource_part:
                return resource_part.split('/')[0]
            return resource_part
        return None
    except IndexError:
        return None

def tag_resource_with_service_api(arn, tags, service):
    """
    Aplica tags usando la API específica del servicio
    Solo para servicios que NO están soportados por Resource Groups Tagging API
    Retorna True si fue exitoso, False si falló
    """
    try:
        if service == 'appconfig':
            client = boto3.client('appconfig')
            # Convertir tags a formato de AppConfig
            appconfig_tags = {key: value for key, value in tags.items()}
            client.tag_resource(ResourceArn=arn, Tags=appconfig_tags)
            return True
        elif service == 's3':
            client = boto3.client('s3')
            bucket_name = arn.split(':::')[-1]
            
            # Obtener tags existentes del bucket
            existing_tags = {}
            try:
                response = client.get_bucket_tagging(Bucket=bucket_name)
                for tag in response.get('TagSet', []):
                    existing_tags[tag['Key']] = tag['Value']
                logger.info(f"   📋 Tags existentes en bucket: {len(existing_tags)} tags")
            except ClientError as e:
                if e.response['Error']['Code'] == 'NoSuchTagSet':
                    logger.info("   📋 Bucket sin tags existentes")
                else:
                    logger.warning(f"   ⚠️  No se pudieron obtener tags existentes: {e}")
            
            # Combinar tags existentes con nuevos (los nuevos tienen prioridad)
            combined_tags = existing_tags.copy()
            combined_tags.update(tags)
            
            # Aplicar tags combinados
            tag_set = [{'Key': k, 'Value': v} for k, v in combined_tags.items()]
            client.put_bucket_tagging(Bucket=bucket_name, Tagging={'TagSet': tag_set})
            logger.info(f"   ✅ Tags aplicados: {len(tags)} nuevos, {len(combined_tags)} total")
            return True
        elif service == 'route53resolver':
            client = boto3.client('route53resolver')
            tag_list = [{'Key': k, 'Value': v} for k, v in tags.items()]
            client.tag_resource(ResourceArn=arn, Tags=tag_list)
            return True
        else:
            # Para servicios no específicamente manejados, no hay API alternativa conocida
            return False
    except Exception as e:
        logger.error(f"Error aplicando tags con API específica para {service}: {str(e)}")
        return False

def apply_tags_to_resources(resource_arns, tags):
    """
    Aplica tags a una lista de recursos AWS usando la API apropiada para cada tipo de recurso
    Procesa los recursos en lotes de 20 para cumplir con las limitaciones de AWS
    """
    tagging_client = boto3.client('resourcegroupstaggingapi')
    
    # Constante para el tamaño del lote (limitación de AWS)
    BATCH_SIZE = 20
    
    try:
        logger.info("🚀 Iniciando proceso de etiquetado...")
        logger.info(f"🏷️  Aplicando tags a {len(resource_arns)} recursos")
        logger.info(f"📋 Tags a aplicar: {tags}")
        
        # Mostrar recursos a etiquetar
        logger.info("📋 Recursos a etiquetar:")
        for i, arn in enumerate(resource_arns, 1):
            logger.info(f"   {i}. {arn}")
        
        # Separar recursos según la API que necesitan
        resource_groups_arns = []
        service_specific_arns = []
        
        # Servicios que NO están soportados por Resource Groups Tagging API
        unsupported_services = {'s3', 'appconfig', 'route53resolver'}
        
        for arn in resource_arns:
            service = get_service_from_arn(arn)
            if service in unsupported_services:
                service_specific_arns.append(arn)
            else:
                resource_groups_arns.append(arn)
        
        logger.info(f"📦 Procesando {len(resource_arns)} recursos:")
        if resource_groups_arns:
            logger.info(f"   - {len(resource_groups_arns)} recursos con Resource Groups Tagging API")
        if service_specific_arns:
            logger.info(f"   - {len(service_specific_arns)} recursos con APIs específicas")
        
        # Variables para acumular resultados
        total_success_count = 0
        total_failed = {}
        
        # Procesar recursos con APIs específicas (uno por uno)
        for arn in service_specific_arns:
            service = get_service_from_arn(arn)
            logger.info(f"🔄 Procesando {arn} con API de {service}...")
            
            if tag_resource_with_service_api(arn, tags, service):
                total_success_count += 1
                logger.info(f"   ✅ Recurso etiquetado exitosamente")
            else:
                total_failed[arn] = {
                    'ErrorCode': 'ServiceSpecificAPIError',
                    'ErrorMessage': f'Error usando API específica de {service}'
                }
                logger.error(f"   ❌ Error etiquetando recurso")
        
        # Procesar recursos con Resource Groups Tagging API (en lotes)
        if resource_groups_arns:
            batches = [resource_groups_arns[i:i + BATCH_SIZE] for i in range(0, len(resource_groups_arns), BATCH_SIZE)]
            total_batches = len(batches)
            
            logger.info(f"📦 Procesando {len(resource_groups_arns)} recursos en {total_batches} lote(s) de máximo {BATCH_SIZE} recursos")
            
            # Procesar cada lote
            for batch_num, batch_arns in enumerate(batches, 1):
                logger.info(f"🔄 Procesando lote {batch_num}/{total_batches} ({len(batch_arns)} recursos)...")
                
                try:
                    # Llamar a la API de tagging para este lote
                    response = tagging_client.tag_resources(
                        ResourceARNList=batch_arns,
                        Tags=tags
                    )
                    
                    batch_failed = response.get("FailedResourcesMap", {})
                    batch_success_count = len(batch_arns) - len(batch_failed)
                    
                    # Acumular resultados
                    total_success_count += batch_success_count
                    total_failed.update(batch_failed)
                    
                    # Mostrar resultados del lote
                    if batch_success_count > 0:
                        logger.info(f"   ✅ Lote {batch_num}: {batch_success_count}/{len(batch_arns)} recursos etiquetados exitosamente")
                    
                    if batch_failed:
                        logger.warning(f"   ⚠️  Lote {batch_num}: {len(batch_failed)} recursos fallaron")
                        for arn, error_info in batch_failed.items():
                            error_code = error_info.get('ErrorCode', 'Desconocido')
                            error_message = error_info.get('ErrorMessage', 'Sin mensaje')
                            logger.error(f"      ❌ {arn}: {error_code} - {error_message}")
                    
                except ClientError as e:
                    error_code = e.response['Error']['Code']
                    error_message = e.response['Error']['Message']
                    logger.error(f"❌ Error en lote {batch_num}: {error_code} - {error_message}")
                    
                    # Marcar todos los recursos del lote como fallidos
                    for arn in batch_arns:
                        total_failed[arn] = {
                            'ErrorCode': error_code,
                            'ErrorMessage': error_message
                        }
        
        # Mostrar resumen final
        logger.info("📊 Resumen final:")
        logger.info(f"   - Total recursos: {len(resource_arns)}")
        logger.info(f"   - Exitosos: {total_success_count}")
        logger.info(f"   - Fallidos: {len(total_failed)}")
        if resource_groups_arns:
            batches_count = len([resource_groups_arns[i:i + BATCH_SIZE] for i in range(0, len(resource_groups_arns), BATCH_SIZE)])
            logger.info(f"   - Lotes procesados: {batches_count}")
        if service_specific_arns:
            logger.info(f"   - Recursos con API específica: {len(service_specific_arns)}")
        
        if total_failed:
            logger.warning("⚠️  Recursos que fallaron:")
            for arn, error_info in total_failed.items():
                error_code = error_info.get('ErrorCode', 'Desconocido')
                error_message = error_info.get('ErrorMessage', 'Sin mensaje')
                logger.error(f"   ❌ {arn}: {error_code} - {error_message}")
        
        return len(total_failed) == 0  # True si todos fueron exitosos
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        logger.error(f"❌ Error de cliente AWS: {error_code} - {error_message}")
        
        if error_code == 'AccessDenied':
            logger.error("💡 Verifica que tienes permisos de etiquetado en AWS")
        elif error_code == 'InvalidParameterException':
            logger.error("💡 Verifica que los ARNs sean válidos")
        
        return False
    except Exception as e:
        logger.error(f"❌ Error general: {str(e)}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Aplicar tags a recursos AWS existentes')
    parser.add_argument('--resource-arns', required=True, 
                       help='ARNs de recursos separados por comas')
    parser.add_argument('--tags', required=True, 
                       help='Tags en formato clave1=valor1,clave2=valor2')
    
    args = parser.parse_args()
    
    # Parsear ARNs
    resource_arns = [arn.strip() for arn in args.resource_arns.split(',') if arn.strip()]
    
    if not resource_arns:
        logger.error("❌ No se proporcionaron ARNs válidos")
        sys.exit(1)
    
    # Validar ARNs
    invalid_arns = [arn for arn in resource_arns if not validate_arn(arn)]
    if invalid_arns:
        logger.error("❌ ARNs inválidos encontrados:")
        for arn in invalid_arns:
            logger.error(f"   - {arn}")
        sys.exit(1)
    
    # Parsear tags
    tags = parse_tags(args.tags)
    if not tags:
        logger.error("❌ No se proporcionaron tags válidos")
        logger.error("💡 Formato esperado: clave1=valor1,clave2=valor2")
        sys.exit(1)
    
    # Aplicar tags
    success = apply_tags_to_resources(resource_arns, tags)
    
    if success:
        logger.info("🎉 Proceso completado exitosamente")
        logger.info("💡 Verifica los tags en la consola de AWS")
        sys.exit(0)
    else:
        logger.error("💥 Proceso falló")
        sys.exit(1)

if __name__ == "__main__":
    main()
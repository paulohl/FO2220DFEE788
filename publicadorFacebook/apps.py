# -*- coding: utf-8 -*-
"""
🔥 APPS.PY - ULTRA ROBUSTO
Configuración de la aplicación publicadorFacebook con signals
"""

from django.apps import AppConfig
import logging

logger = logging.getLogger(__name__)


class PublicadorFacebookConfig(AppConfig):
    """
    Configuración de la aplicación publicadorFacebook
    """
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'publicadorFacebook'
    verbose_name = 'Publicador de Facebook'
    
    def ready(self):
        """
        🔥 Se ejecuta cuando Django inicia
        
        Aquí importamos los signals para que se registren automáticamente.
        Los signals manejan:
        1. Validación de horarios en publicaciones
        2. Reprogramación automática de anuncios
        3. Validación de horarios en anuncios
        """
        try:
            # Importar signals para registrar los @receiver
            import publicadorFacebook.signals
            
            logger.info("✅ Signals de publicadorFacebook registrados correctamente")
            logger.info("   - Validación de horarios en publicaciones")
            logger.info("   - Reprogramación automática de anuncios")
            logger.info("   - Validación de horarios en anuncios")
            
        except ImportError as e:
            logger.error(f"❌ Error importando signals: {e}")
            logger.error(f"   Verifica que existe publicadorFacebook/signals.py")
            
        except Exception as e:
            logger.error(f"❌ Error registrando signals: {e}")
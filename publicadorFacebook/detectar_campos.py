#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script para detectar los campos reales del modelo PublicacionGrupoFacebook
Ejecutar: docker exec facebook_144_ultima_version-web-1 python /tmp/detectar_campos.py
"""

import os
import django
import sys

# Configurar Django
sys.path.append('/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

try:
    django.setup()
except:
    try:
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings')
        django.setup()
    except Exception as e:
        print(f"❌ No se pudo configurar Django: {e}")
        sys.exit(1)

try:
    from publicadorFacebook.models import PublicacionGrupoFacebook
except ImportError as e:
    print(f"❌ No se pudo importar el modelo: {e}")
    sys.exit(1)

print("=" * 70)
print("📊 CAMPOS DEL MODELO PublicacionGrupoFacebook")
print("=" * 70)
print()

# Obtener todos los campos
fields = PublicacionGrupoFacebook._meta.get_fields()

print("CAMPOS ENCONTRADOS:")
print("-" * 70)

for field in fields:
    field_name = field.name
    field_type = field.__class__.__name__
    
    # Obtener información adicional
    if hasattr(field, 'null'):
        nullable = "NULL" if field.null else "NOT NULL"
    else:
        nullable = "N/A"
    
    if hasattr(field, 'blank'):
        blankable = "BLANK" if field.blank else "REQUIRED"
    else:
        blankable = "N/A"
    
    print(f"  • {field_name:30} {field_type:20} {nullable:10} {blankable}")

print()
print("=" * 70)
print("🔍 CAMPOS POR TIPO")
print("=" * 70)
print()

# Buscar campos relacionados con fechas
date_fields = [f.name for f in fields if 'date' in f.__class__.__name__.lower() or 'fecha' in f.name.lower()]
print(f"📅 Campos de fecha: {', '.join(date_fields) if date_fields else 'Ninguno'}")

# Buscar campos booleanos
bool_fields = [f.name for f in fields if 'boolean' in f.__class__.__name__.lower()]
print(f"✓ Campos booleanos: {', '.join(bool_fields) if bool_fields else 'Ninguno'}")

# Buscar campos de texto
text_fields = [f.name for f in fields if 'char' in f.__class__.__name__.lower() or 'text' in f.__class__.__name__.lower()]
print(f"📝 Campos de texto: {', '.join(text_fields) if text_fields else 'Ninguno'}")

# Buscar campos numéricos
int_fields = [f.name for f in fields if 'integer' in f.__class__.__name__.lower()]
print(f"🔢 Campos numéricos: {', '.join(int_fields) if int_fields else 'Ninguno'}")

# Buscar relaciones
fk_fields = [f.name for f in fields if 'ForeignKey' in f.__class__.__name__]
print(f"🔗 Claves foráneas: {', '.join(fk_fields) if fk_fields else 'Ninguno'}")

print()
print("=" * 70)
print("✅ Análisis completado")
print("=" * 70)

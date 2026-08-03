---
tipo: moc
---

# Índice del Oráculo

Mapa de contenidos. Todo el vault cuelga de acá.

## Núcleo
- [[../Persona/Luciano Marcos Rossi]] — nota central
- [[Metodología]] — **cómo funciona y qué no puede hacer**

## Astrología
- [[../Astrología/Carta Natal]] — análisis completo
- [[../Astrología/Tránsitos]] — estado vigente
- [[../Astrología/Revoluciones Solares]]

## Otros sistemas
- [[../Numerología/Perfil]] · [[../Numerología/Años Personales]]
- [[../Tradiciones/BaZi]] — BaZi, maya, feng shui, ayurveda, cábala, celta
- [[../Tarot/Historial]]

## Decisiones (Oráculo Estratégico)
- [[../Decisiones/Protocolo Estratégico]] — **15 marcos, activación automática**
- [[../Decisiones/Historial]] — registro de decisiones y resultados

## Aprendizaje
- [[../Predicciones/Seguimiento]] — precisión medida
- [[../Patrones/Detectados]] — qué se confirmó y qué se refutó

## Registro personal
- [[../Sueños/Diario]] · [[../Salud/Hábitos]]
- [[../Quiromancia/Mano Derecha]] · [[../Quiromancia/Mano Izquierda]]

## Áreas
- [[../Trabajo/Índice]] · [[../Relaciones/Índice]] · [[../Política/Índice]]
- [[../Creatividad/Índice]] · [[../Objetivos/Índice]]

## Motores

| Comando | Qué hace |
|---|---|
| `python3 engine/verificar_hora.py` | **Auditoría de la hora de nacimiento** |
| `python3 engine/natal.py` | Carta natal completa |
| `python3 engine/transitos.py --ciclos` | Tránsitos, progresiones, ciclos |
| `python3 engine/numerologia.py` | Perfil y ciclos numerológicos |
| `python3 engine/tradiciones.py` | BaZi, maya, feng shui, ayurveda |
| `python3 engine/sorteos.py tarot\|iching\|runas` | Sorteos con registro |
| `python3 engine/hermes.py briefing` | **Memoria ejecutiva** |
| `python3 engine/registro.py validar` | **Precisión medida** |
| `python3 engine/decisiones.py nueva --archivo d.json` | Registrar una decisión |
| `python3 engine/decisiones.py pendientes` | **Revisiones vencidas** |
| `python3 engine/decisiones.py aprender` | **Calibración y sesgos recurrentes** |
| `python3 engine/informe.py --markdown` | Dossier completo |

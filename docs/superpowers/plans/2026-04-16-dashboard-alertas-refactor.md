# Dashboard + Centro de Alertas — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Separar el dashboard principal (carga instantánea) del centro de alertas (vista dedicada con carga diferida vía AJAX), eliminando la latencia de producción causada por los 8 cálculos síncronos de alertas.

**Architecture:** La vista `dashboard()` queda con solo 2 queries COUNT. Dos nuevos endpoints AJAX sirven (1) los conteos de alertas para el inicio y (2) el HTML pre-renderizado de las tarjetas de alertas para la vista dedicada `centro_alertas`. La lógica de cálculo de alertas en `gestion/services/alertas.py` no se modifica.

**Tech Stack:** Django 4.x, Bootstrap 5.3, Font Awesome 6, JavaScript vanilla (fetch API), `render_to_string` de Django para HTML pre-renderizado.

---

## Mapa de archivos

| Acción | Archivo | Responsabilidad |
|---|---|---|
| Crear | `templates/gestion/alertas/_detalle_alertas.html` | Partial con las 8 tarjetas de alertas (sin filtro) |
| Crear | `templates/gestion/alertas/index.html` | Vista dedicada de alertas con progreso y filtro |
| Modificar | `templates/gestion/dashboard/index.html` | Inicio liviano: stats AJAX, 8 contadores con spinner, botón CTA |
| Modificar | `gestion/views/dashboard.py` | Agregar `centro_alertas`, `api_conteos_alertas`, `api_detalle_alertas`; refactorizar `dashboard` |
| Modificar | `gestion/views/__init__.py` | Exportar las 3 nuevas vistas |
| Modificar | `gestion/urls.py` | Registrar 3 nuevas URLs |
| Crear | `gestion/tests/__init__.py` | Habilitar paquete de tests |
| Crear | `gestion/tests/test_dashboard.py` | Tests del dashboard y endpoints AJAX |

---

## Task 1: Crear el partial `_detalle_alertas.html`

**Files:**
- Create: `templates/gestion/alertas/_detalle_alertas.html`

Este partial contiene las 8 tarjetas de alertas extraídas del dashboard actual. Recibe el mismo contexto que recibía el dashboard. No incluye el filtro (ese vive en el template principal de `centro_alertas`).

- [ ] **Step 1: Crear el directorio y el partial**

Crear `templates/gestion/alertas/_detalle_alertas.html` con el siguiente contenido:

```html
{# Partial: tarjetas de alertas. Recibe el mismo contexto que el dashboard. #}
<div class="row">
    <!-- Alertas de Vencimiento de Contrato -->
    <div class="col-lg-6 mb-4">
        <div class="card alert-card alert-vencimiento">
            <div class="card-header" style="background-color: var(--avenida-orange); color: white;">
                <div class="d-flex flex-column flex-lg-row justify-content-between align-items-lg-center">
                    <div>
                        <h5 class="mb-0">
                            <i class="fas fa-exclamation-triangle"></i>
                            Alertas de Vencimiento de Contrato
                            <span class="badge bg-light text-dark ms-2">{{ total_alertas_vencimiento }}</span>
                        </h5>
                    </div>
                    <a
                        href="{% url 'gestion:exportar_alertas_vencimiento' %}"
                        class="btn btn-light btn-sm mt-3 mt-lg-0 text-warning fw-semibold{% if total_alertas_vencimiento == 0 %} disabled{% endif %}"
                        {% if total_alertas_vencimiento == 0 %}aria-disabled="true"{% endif %}
                    >
                        <i class="fas fa-file-excel"></i> Exportar Excel
                    </a>
                </div>
            </div>
            <div class="card-body">
                {% if contratos_por_vencer %}
                    <div class="table-responsive alert-collapsible" data-collapsed="true" style="max-height: 64px; overflow: hidden; position: relative;">
                        <table class="table table-sm">
                            <thead>
                                <tr><th>Contrato</th><th>Tercero</th><th>Vence</th><th>Días</th></tr>
                            </thead>
                            <tbody>
                                {% for item in contratos_por_vencer %}
                                <tr>
                                    <td>
                                        <strong>{{ item.contrato.num_contrato }}</strong><br>
                                        <small class="text-muted">{% if item.contrato.local %}{{ item.contrato.local.nombre_comercial_stand }}{% else %}-{% endif %}</small>
                                    </td>
                                    <td>
                                        {% if item.contrato.obtener_tercero %}
                                            {{ item.contrato.obtener_tercero.razon_social }}
                                            {% if item.contrato.tipo_contrato_cliente_proveedor == 'PROVEEDOR' %}
                                                <br><span class="badge bg-success">Proveedor</span>
                                            {% else %}
                                                <br><span class="badge bg-primary">Cliente</span>
                                            {% endif %}
                                        {% else %}
                                            <span class="text-muted">Sin tercero asignado</span>
                                        {% endif %}
                                    </td>
                                    <td>{{ item.fecha_final_actualizada|date:"d \d\e F \d\e Y" }}</td>
                                    <td><span class="badge bg-warning">Próximo a vencer</span></td>
                                </tr>
                                {% endfor %}
                            </tbody>
                        </table>
                        <div class="fade-overlay" style="display: block; position: absolute; left: 0; right: 0; bottom: 0; height: 24px; background: linear-gradient(to bottom, rgba(255,255,255,0), rgba(255,255,255,1));"></div>
                    </div>
                    <button class="btn btn-link p-0 mt-2 toggle-alert" type="button">Ver más</button>
                {% else %}
                    <div class="text-center text-muted">
                        <i class="fas fa-check-circle fa-2x mb-2"></i>
                        <p>No hay contratos por vencer en los próximos 90 días</p>
                    </div>
                {% endif %}
            </div>
        </div>
    </div>

    <!-- Alertas de Pólizas Críticas -->
    <div class="col-lg-6 mb-4">
        <div class="card alert-card alert-poliza">
            <div class="card-header" style="background-color: var(--avenida-magenta); color: white;">
                <div class="d-flex flex-column flex-lg-row justify-content-between align-items-lg-center">
                    <div>
                        <h5 class="mb-0">
                            <i class="fas fa-shield-alt"></i>
                            Alertas de Pólizas
                            <span class="badge bg-light text-dark ms-2">{{ total_polizas_criticas }}</span>
                        </h5>
                    </div>
                    <a
                        href="{% url 'gestion:exportar_alertas_polizas' %}"
                        class="btn btn-light btn-sm mt-3 mt-lg-0 text-danger fw-semibold{% if total_polizas_criticas == 0 %} disabled{% endif %}"
                        {% if total_polizas_criticas == 0 %}aria-disabled="true"{% endif %}
                    >
                        <i class="fas fa-file-excel"></i> Exportar Excel
                    </a>
                </div>
            </div>
            <div class="card-body">
                {% if polizas_criticas %}
                    {% if hay_polizas_con_colchon %}
                    <p class="small text-muted mb-2">
                        <i class="fas fa-info-circle"></i>
                        La alerta considera la <strong>vigencia real</strong> (fecha formal menos colchón cuando aplica) para renovación.
                    </p>
                    {% endif %}
                    <div class="table-responsive alert-collapsible" data-collapsed="true" style="max-height: 64px; overflow: hidden; position: relative;">
                        <table class="table table-sm">
                            <thead>
                                <tr><th>Póliza</th><th>Contrato</th><th>Estado</th><th>Vence</th></tr>
                            </thead>
                            <tbody>
                                {% for poliza in polizas_criticas %}
                                <tr>
                                    <td>
                                        <strong>{{ poliza.numero_poliza }}</strong><br>
                                        <small class="text-muted">{{ poliza.get_tipo_display }}</small>
                                    </td>
                                    <td>{{ poliza.contrato.num_contrato }}</td>
                                    <td>
                                        {% if poliza.obtener_estado_vigencia == 'Vencida' %}
                                            <span class="badge bg-danger">
                                                <i class="fas fa-times-circle"></i> {{ poliza.obtener_estado_legible }}{% if poliza.tiene_colchon and poliza.meses_colchon %} <small>(vigencia real)</small>{% endif %}
                                            </span>
                                        {% elif poliza.obtener_dias_para_vencer <= 30 %}
                                            <span class="badge bg-warning">
                                                <i class="fas fa-exclamation-triangle"></i> {{ poliza.obtener_estado_legible }}{% if poliza.tiene_colchon and poliza.meses_colchon %} <small>(vigencia real)</small>{% endif %}
                                            </span>
                                        {% else %}
                                            <span class="badge bg-success">
                                                <i class="fas fa-check-circle"></i> {{ poliza.obtener_estado_legible }}
                                            </span>
                                        {% endif %}
                                    </td>
                                    <td>
                                        {% if poliza.tiene_colchon and poliza.fecha_vencimiento_real and poliza.fecha_vencimiento_real != poliza.fecha_vencimiento %}
                                            <span>{{ poliza.obtener_fecha_vencimiento_efectiva|date:"d \d\e F \d\e Y" }}</span><br>
                                            <small class="text-muted">Formal: {{ poliza.fecha_vencimiento|date:"d \d\e F \d\e Y" }}</small>
                                        {% else %}
                                            {{ poliza.fecha_vencimiento|date:"d \d\e F \d\e Y" }}
                                        {% endif %}
                                    </td>
                                </tr>
                                {% endfor %}
                            </tbody>
                        </table>
                        <div class="fade-overlay" style="display: block; position: absolute; left: 0; right: 0; bottom: 0; height: 24px; background: linear-gradient(to bottom, rgba(255,255,255,0), rgba(255,255,255,1));"></div>
                    </div>
                    <button class="btn btn-link p-0 mt-2 toggle-alert" type="button">Ver más</button>
                {% else %}
                    <div class="text-center text-muted">
                        <i class="fas fa-check-circle fa-2x mb-2"></i>
                        <p>Todas las pólizas están en orden</p>
                    </div>
                {% endif %}
            </div>
        </div>
    </div>

    <!-- Alertas de Renovación (Preaviso) -->
    <div class="col-lg-6 mb-4">
        <div class="card alert-card alert-preaviso">
            <div class="card-header" style="background-color: var(--avenida-cyan); color: white;">
                <div class="d-flex flex-column flex-lg-row justify-content-between align-items-lg-center">
                    <div>
                        <h5 class="mb-0">
                            <i class="fas fa-clock"></i>
                            Alertas de Renovación (Preaviso)
                            <span class="badge bg-light text-dark ms-2">{{ total_alertas_preaviso }}</span>
                        </h5>
                    </div>
                    <a
                        href="{% url 'gestion:exportar_alertas_preaviso' %}"
                        class="btn btn-light btn-sm mt-3 mt-lg-0 text-info fw-semibold{% if total_alertas_preaviso == 0 %} disabled{% endif %}"
                        {% if total_alertas_preaviso == 0 %}aria-disabled="true"{% endif %}
                    >
                        <i class="fas fa-file-excel"></i> Exportar Excel
                    </a>
                </div>
            </div>
            <div class="card-body">
                {% if alertas_preaviso_renovacion %}
                    <div class="table-responsive alert-collapsible" data-collapsed="true" style="max-height: 64px; overflow: hidden; position: relative;">
                        <table class="table table-sm">
                            <thead>
                                <tr><th>Contrato</th><th>Tercero</th><th>Vence</th><th>Preaviso</th></tr>
                            </thead>
                            <tbody>
                                {% for item in alertas_preaviso_renovacion %}
                                <tr>
                                    <td>
                                        <strong>{{ item.contrato.num_contrato }}</strong><br>
                                        <small class="text-muted">{% if item.contrato.local %}{{ item.contrato.local.nombre_comercial_stand }}{% else %}-{% endif %}</small>
                                    </td>
                                    <td>
                                        {% if item.contrato.obtener_tercero %}
                                            {{ item.contrato.obtener_tercero.razon_social }}
                                            {% if item.contrato.tipo_contrato_cliente_proveedor == 'PROVEEDOR' %}
                                                <br><span class="badge bg-success">Proveedor</span>
                                            {% else %}
                                                <br><span class="badge bg-primary">Cliente</span>
                                            {% endif %}
                                        {% else %}
                                            <span class="text-muted">Sin tercero asignado</span>
                                        {% endif %}
                                    </td>
                                    <td>{{ item.fecha_final_actualizada|date:"d \d\e F \d\e Y" }}</td>
                                    <td><span class="badge bg-warning">{{ item.contrato.dias_preaviso_no_renovacion }} días</span></td>
                                </tr>
                                {% endfor %}
                            </tbody>
                        </table>
                        <div class="fade-overlay" style="display: block; position: absolute; left: 0; right: 0; bottom: 0; height: 24px; background: linear-gradient(to bottom, rgba(255,255,255,0), rgba(255,255,255,1));"></div>
                    </div>
                    <button class="btn btn-link p-0 mt-2 toggle-alert" type="button">Ver más</button>
                {% else %}
                    <div class="text-center text-muted">
                        <i class="fas fa-check-circle fa-2x mb-2"></i>
                        <p>No hay alertas de preaviso activas</p>
                    </div>
                {% endif %}
            </div>
        </div>
    </div>

    <!-- Alertas de Ajuste de IPC -->
    <div class="col-lg-6 mb-4">
        <div class="card alert-card alert-ipc">
            <div class="card-header" style="background-color: var(--avenida-green); color: white;">
                <div class="d-flex flex-column flex-lg-row justify-content-between align-items-lg-center">
                    <div>
                        <h5 class="mb-0">
                            <i class="fas fa-percentage"></i>
                            Alertas de Ajuste de IPC en Facturación
                            <span class="badge bg-light text-dark ms-2">{{ total_alertas_ipc }}</span>
                        </h5>
                        <small class="d-block mt-2">
                            <span class="badge bg-danger me-1"><i class="fas fa-exclamation-circle"></i> 0-1 mes</span>
                            <span class="badge bg-warning me-1"><i class="fas fa-exclamation-triangle"></i> 2 meses</span>
                            <span class="badge bg-success me-1"><i class="fas fa-check-circle"></i> 3+ meses</span>
                        </small>
                    </div>
                    <div class="d-flex gap-2 mt-3 mt-lg-0">
                        <a href="{% url 'gestion:lista_ipc_historico' %}" class="btn btn-light btn-sm text-success fw-semibold">
                            <i class="fas fa-calculator"></i> Calcular
                        </a>
                        <a
                            href="{% url 'gestion:exportar_alertas_ipc' %}"
                            class="btn btn-light btn-sm text-success fw-semibold{% if total_alertas_ipc == 0 %} disabled{% endif %}"
                            {% if total_alertas_ipc == 0 %}aria-disabled="true"{% endif %}
                        >
                            <i class="fas fa-file-excel"></i> Exportar IPC
                        </a>
                    </div>
                </div>
            </div>
            <div class="card-body">
                {% if alertas_ipc %}
                    <div class="table-responsive alert-collapsible" data-collapsed="true" style="max-height: 64px; overflow: hidden; position: relative;">
                        <table class="table table-sm">
                            <thead>
                                <tr><th>Contrato</th><th>Tercero</th><th>Mes Ajuste</th><th>Estado</th></tr>
                            </thead>
                            <tbody>
                                {% for alerta in alertas_ipc %}
                                <tr style="{% if alerta.color_alerta == 'danger' %}background-color: #fff5f5;{% elif alerta.color_alerta == 'warning' %}background-color: #fffbf0;{% endif %}">
                                    <td>
                                        <strong>{{ alerta.contrato.num_contrato }}</strong><br>
                                        <small class="text-muted">{% if alerta.contrato.local %}{{ alerta.contrato.local.nombre_comercial_stand }}{% else %}-{% endif %}</small>
                                    </td>
                                    <td>
                                        {% if alerta.contrato.obtener_tercero %}
                                            {{ alerta.contrato.obtener_tercero.razon_social }}
                                            {% if alerta.contrato.tipo_contrato_cliente_proveedor == 'PROVEEDOR' %}
                                                <br><span class="badge bg-success">Proveedor</span>
                                            {% else %}
                                                <br><span class="badge bg-primary">Cliente</span>
                                            {% endif %}
                                        {% else %}
                                            <span class="text-muted">Sin tercero asignado</span>
                                        {% endif %}
                                    </td>
                                    <td>
                                        <span class="badge bg-info">{{ alerta.mes_ajuste }}</span><br>
                                        <small class="text-muted">{{ alerta.condicion_ipc }}</small>
                                        {% if alerta.otrosi_modificador %}
                                            <br><small class="text-info"><i class="fas fa-file-signature"></i> {{ alerta.otrosi_modificador }}</small>
                                        {% endif %}
                                    </td>
                                    <td>
                                        <span class="badge bg-{{ alerta.color_alerta }}">
                                            {% if alerta.meses_restantes < 0 %}
                                                <i class="fas fa-exclamation-circle"></i> Vencida ({{ alerta.meses_restantes_abs }} meses)
                                            {% elif alerta.meses_restantes == 0 %}
                                                <i class="fas fa-exclamation-circle"></i> Este mes
                                            {% elif alerta.meses_restantes == 1 %}
                                                <i class="fas fa-exclamation-circle"></i> 1 mes
                                            {% elif alerta.meses_restantes == 2 %}
                                                <i class="fas fa-exclamation-triangle"></i> 2 meses
                                            {% elif alerta.meses_restantes == 3 %}
                                                <i class="fas fa-info-circle"></i> 3 meses
                                            {% else %}
                                                <i class="fas fa-check-circle"></i> {{ alerta.meses_restantes }} meses
                                            {% endif %}
                                        </span>
                                    </td>
                                </tr>
                                {% endfor %}
                            </tbody>
                        </table>
                        <div class="fade-overlay" style="display: block; position: absolute; left: 0; right: 0; bottom: 0; height: 24px; background: linear-gradient(to bottom, rgba(255,255,255,0), rgba(255,255,255,1));"></div>
                    </div>
                    <button class="btn btn-link p-0 mt-2 toggle-alert" type="button">Ver más</button>
                {% else %}
                    <div class="text-center text-muted">
                        <i class="fas fa-check-circle fa-2x mb-2"></i>
                        <p>No hay alertas de ajuste de IPC activas</p>
                    </div>
                {% endif %}
            </div>
        </div>
    </div>

    <!-- Alertas de Ajuste de Salario Mínimo -->
    <div class="col-lg-6 mb-4">
        <div class="card alert-card alert-salario-minimo">
            <div class="card-header" style="background-color: #28a745; color: white;">
                <div class="d-flex flex-column flex-lg-row justify-content-between align-items-lg-center">
                    <div>
                        <h5 class="mb-0">
                            <i class="fas fa-dollar-sign"></i>
                            Alertas de Ajuste de Salario Mínimo
                            <span class="badge bg-light text-dark ms-2">{{ total_alertas_salario_minimo }}</span>
                        </h5>
                        <small class="d-block mt-2">
                            <span class="badge bg-danger me-1"><i class="fas fa-exclamation-circle"></i> 0-1 mes</span>
                            <span class="badge bg-warning me-1"><i class="fas fa-exclamation-triangle"></i> 2 meses</span>
                            <span class="badge bg-success me-1"><i class="fas fa-check-circle"></i> 3+ meses</span>
                        </small>
                    </div>
                    <div class="d-flex gap-2 mt-3 mt-lg-0">
                        <a href="{% url 'gestion:lista_salario_minimo_historico' %}" class="btn btn-light btn-sm text-success fw-semibold">
                            <i class="fas fa-calculator"></i> Calcular
                        </a>
                        <a
                            href="{% url 'gestion:exportar_alertas_salario_minimo' %}"
                            class="btn btn-light btn-sm text-success fw-semibold{% if total_alertas_salario_minimo == 0 %} disabled{% endif %}"
                            {% if total_alertas_salario_minimo == 0 %}aria-disabled="true"{% endif %}
                        >
                            <i class="fas fa-file-excel"></i> Exportar
                        </a>
                    </div>
                </div>
            </div>
            <div class="card-body">
                {% if alertas_salario_minimo %}
                    <div class="table-responsive alert-collapsible" data-collapsed="true" style="max-height: 64px; overflow: hidden; position: relative;">
                        <table class="table table-sm">
                            <thead>
                                <tr><th>Contrato</th><th>Tercero</th><th>Mes Ajuste</th><th>Estado</th></tr>
                            </thead>
                            <tbody>
                                {% for alerta in alertas_salario_minimo %}
                                <tr style="{% if alerta.color_alerta == 'danger' %}background-color: #fff5f5;{% elif alerta.color_alerta == 'warning' %}background-color: #fffbf0;{% endif %}">
                                    <td>
                                        <strong>{{ alerta.contrato.num_contrato }}</strong><br>
                                        <small class="text-muted">{% if alerta.contrato.local %}{{ alerta.contrato.local.nombre_comercial_stand }}{% else %}-{% endif %}</small>
                                    </td>
                                    <td>
                                        {% if alerta.contrato.obtener_tercero %}
                                            {{ alerta.contrato.obtener_tercero.razon_social }}
                                            {% if alerta.contrato.tipo_contrato_cliente_proveedor == 'PROVEEDOR' %}
                                                <br><span class="badge bg-success">Proveedor</span>
                                            {% else %}
                                                <br><span class="badge bg-primary">Cliente</span>
                                            {% endif %}
                                        {% else %}
                                            <span class="text-muted">Sin tercero asignado</span>
                                        {% endif %}
                                    </td>
                                    <td>
                                        <span class="badge bg-success">{{ alerta.mes_ajuste }}</span><br>
                                        <small class="text-muted">{{ alerta.condicion_salario_minimo }}</small>
                                        {% if alerta.otrosi_modificador %}
                                            <br><small class="text-info"><i class="fas fa-file-signature"></i> {{ alerta.otrosi_modificador }}</small>
                                        {% endif %}
                                    </td>
                                    <td>
                                        <span class="badge bg-{{ alerta.color_alerta }}">
                                            {% if alerta.meses_restantes < 0 %}
                                                <i class="fas fa-exclamation-circle"></i> Vencida ({{ alerta.meses_restantes_abs }} meses)
                                            {% elif alerta.meses_restantes == 0 %}
                                                <i class="fas fa-exclamation-circle"></i> Este mes
                                            {% elif alerta.meses_restantes == 1 %}
                                                <i class="fas fa-exclamation-circle"></i> 1 mes
                                            {% elif alerta.meses_restantes == 2 %}
                                                <i class="fas fa-exclamation-triangle"></i> 2 meses
                                            {% elif alerta.meses_restantes == 3 %}
                                                <i class="fas fa-info-circle"></i> 3 meses
                                            {% else %}
                                                <i class="fas fa-check-circle"></i> {{ alerta.meses_restantes }} meses
                                            {% endif %}
                                        </span>
                                    </td>
                                </tr>
                                {% endfor %}
                            </tbody>
                        </table>
                        <div class="fade-overlay" style="display: block; position: absolute; left: 0; right: 0; bottom: 0; height: 24px; background: linear-gradient(to bottom, rgba(255,255,255,0), rgba(255,255,255,1));"></div>
                    </div>
                    <button class="btn btn-link p-0 mt-2 toggle-alert" type="button">Ver más</button>
                {% else %}
                    <div class="text-center text-muted">
                        <i class="fas fa-check-circle fa-2x mb-2"></i>
                        <p>No hay alertas de ajuste de Salario Mínimo</p>
                    </div>
                {% endif %}
            </div>
        </div>
    </div>

    <!-- Alertas de Pólizas Requeridas No Aportadas -->
    <div class="col-lg-6 mb-4">
        <div class="card alert-card alert-poliza-requerida">
            <div class="card-header" style="background-color: var(--avenida-magenta); color: white;">
                <div class="d-flex flex-column flex-lg-row justify-content-between align-items-lg-center">
                    <div>
                        <h5 class="mb-0">
                            <i class="fas fa-exclamation-circle"></i>
                            Alertas de Pólizas Requeridas No Aportadas
                            <span class="badge bg-light text-dark ms-2">{{ total_alertas_polizas_requeridas }}</span>
                        </h5>
                    </div>
                    <a
                        href="{% url 'gestion:exportar_alertas_polizas_requeridas' %}"
                        class="btn btn-light btn-sm mt-3 mt-lg-0 text-danger fw-semibold{% if total_alertas_polizas_requeridas == 0 %} disabled{% endif %}"
                        {% if total_alertas_polizas_requeridas == 0 %}aria-disabled="true"{% endif %}
                    >
                        <i class="fas fa-file-excel"></i> Exportar Excel
                    </a>
                </div>
            </div>
            <div class="card-body">
                {% if alertas_polizas_requeridas %}
                    <div class="table-responsive alert-collapsible" data-collapsed="true" style="max-height: 64px; overflow: hidden; position: relative;">
                        <table class="table table-sm">
                            <thead>
                                <tr><th>Contrato</th><th>Tercero</th><th>Tipo Póliza</th><th>Estado</th></tr>
                            </thead>
                            <tbody>
                                {% for alerta in alertas_polizas_requeridas %}
                                <tr>
                                    <td>
                                        <strong>{{ alerta.contrato.num_contrato }}</strong><br>
                                        <small class="text-muted">{% if alerta.contrato.local %}{{ alerta.contrato.local.nombre_comercial_stand }}{% else %}-{% endif %}</small>
                                    </td>
                                    <td>
                                        {% if alerta.contrato.obtener_tercero %}
                                            {{ alerta.contrato.obtener_tercero.razon_social }}
                                            {% if alerta.contrato.tipo_contrato_cliente_proveedor == 'PROVEEDOR' %}
                                                <br><span class="badge bg-success">Proveedor</span>
                                            {% else %}
                                                <br><span class="badge bg-primary">Cliente</span>
                                            {% endif %}
                                        {% else %}
                                            <span class="text-muted">Sin tercero asignado</span>
                                        {% endif %}
                                    </td>
                                    <td>
                                        <span class="badge bg-info">{{ alerta.nombre_poliza }}</span>
                                        {% if alerta.otrosi_modificador %}
                                            <br><small class="text-info"><i class="fas fa-file-signature"></i> {{ alerta.otrosi_modificador }}</small>
                                        {% endif %}
                                    </td>
                                    <td>
                                        {% if alerta.tiene_poliza %}
                                            <span class="badge bg-warning"><i class="fas fa-exclamation-triangle"></i> Póliza vencida</span>
                                        {% else %}
                                            <span class="badge bg-danger"><i class="fas fa-times-circle"></i> Sin póliza</span>
                                        {% endif %}
                                    </td>
                                </tr>
                                {% endfor %}
                            </tbody>
                        </table>
                        <div class="fade-overlay" style="display: block; position: absolute; left: 0; right: 0; bottom: 0; height: 24px; background: linear-gradient(to bottom, rgba(255,255,255,0), rgba(255,255,255,1));"></div>
                    </div>
                    <button class="btn btn-link p-0 mt-2 toggle-alert" type="button">Ver más</button>
                {% else %}
                    <div class="text-center text-muted">
                        <i class="fas fa-check-circle fa-2x mb-2"></i>
                        <p>Todas las pólizas requeridas están aportadas y vigentes</p>
                    </div>
                {% endif %}
            </div>
        </div>
    </div>

    <!-- Alertas de Terminación Anticipada -->
    <div class="col-lg-6 mb-4">
        <div class="card alert-card alert-terminacion">
            <div class="card-header" style="background-color: var(--avenida-orange); color: white;">
                <div class="d-flex flex-column flex-lg-row justify-content-between align-items-lg-center">
                    <div>
                        <h5 class="mb-0">
                            <i class="fas fa-hourglass-half"></i>
                            Alertas de Terminación Anticipada
                            <span class="badge bg-light text-dark ms-2">{{ total_alertas_terminacion }}</span>
                        </h5>
                    </div>
                    <a
                        href="{% url 'gestion:exportar_alertas_terminacion' %}"
                        class="btn btn-light btn-sm mt-3 mt-lg-0 text-warning fw-semibold{% if total_alertas_terminacion == 0 %} disabled{% endif %}"
                        {% if total_alertas_terminacion == 0 %}aria-disabled="true"{% endif %}
                    >
                        <i class="fas fa-file-excel"></i> Exportar Excel
                    </a>
                </div>
            </div>
            <div class="card-body">
                {% if alertas_terminacion %}
                    <div class="table-responsive alert-collapsible" data-collapsed="true" style="max-height: 64px; overflow: hidden; position: relative;">
                        <table class="table table-sm">
                            <thead>
                                <tr><th>Contrato</th><th>Tercero</th><th>Vence</th><th>Días Restantes</th></tr>
                            </thead>
                            <tbody>
                                {% for alerta in alertas_terminacion %}
                                <tr>
                                    <td>
                                        <strong>{{ alerta.contrato.num_contrato }}</strong><br>
                                        <small class="text-muted">{% if alerta.contrato.local %}{{ alerta.contrato.local.nombre_comercial_stand }}{% else %}-{% endif %}</small>
                                    </td>
                                    <td>
                                        {% if alerta.contrato.obtener_tercero %}
                                            {{ alerta.contrato.obtener_tercero.razon_social }}
                                            {% if alerta.contrato.tipo_contrato_cliente_proveedor == 'PROVEEDOR' %}
                                                <br><span class="badge bg-success">Proveedor</span>
                                            {% else %}
                                                <br><span class="badge bg-primary">Cliente</span>
                                            {% endif %}
                                        {% else %}
                                            <span class="text-muted">Sin tercero asignado</span>
                                        {% endif %}
                                    </td>
                                    <td>{{ alerta.fecha_final_actualizada|date:"d \d\e F \d\e Y" }}</td>
                                    <td>
                                        <span class="badge bg-warning">{{ alerta.dias_restantes }} días</span><br>
                                        <small class="text-muted">Límite: {{ alerta.fecha_limite_terminacion|date:"d/m/Y" }}</small>
                                        {% if alerta.otrosi_modificador %}
                                            <br><small class="text-info"><i class="fas fa-file-signature"></i> {{ alerta.otrosi_modificador }}</small>
                                        {% endif %}
                                    </td>
                                </tr>
                                {% endfor %}
                            </tbody>
                        </table>
                        <div class="fade-overlay" style="display: block; position: absolute; left: 0; right: 0; bottom: 0; height: 24px; background: linear-gradient(to bottom, rgba(255,255,255,0), rgba(255,255,255,1));"></div>
                    </div>
                    <button class="btn btn-link p-0 mt-2 toggle-alert" type="button">Ver más</button>
                {% else %}
                    <div class="text-center text-muted">
                        <i class="fas fa-check-circle fa-2x mb-2"></i>
                        <p>No hay contratos dentro del período de terminación anticipada</p>
                    </div>
                {% endif %}
            </div>
        </div>
    </div>
</div>

<script>
document.addEventListener('DOMContentLoaded', function() {
  document.addEventListener('click', function(e){
    const btn = e.target.closest('.toggle-alert');
    if (!btn) return;
    e.preventDefault();
    const cardBody = btn.closest('.card-body');
    if (!cardBody) return;
    const container = cardBody.querySelector('.alert-collapsible');
    if (!container) return;
    const collapsed = container.getAttribute('data-collapsed') === 'true';
    if (collapsed) {
      container.style.maxHeight = '40vh';
      container.style.overflowY = 'auto';
      const overlay = container.querySelector('.fade-overlay');
      if (overlay) overlay.style.display = 'none';
      container.setAttribute('data-collapsed', 'false');
      btn.textContent = 'Ver menos';
      btn.setAttribute('aria-expanded', 'true');
    } else {
      container.style.maxHeight = '64px';
      container.style.overflowY = 'hidden';
      const overlay = container.querySelector('.fade-overlay');
      if (overlay) overlay.style.display = 'block';
      container.setAttribute('data-collapsed', 'true');
      btn.textContent = 'Ver más';
      btn.setAttribute('aria-expanded', 'false');
    }
  });
});
</script>
```

- [ ] **Step 2: Commit**

```bash
git add templates/gestion/alertas/_detalle_alertas.html
git commit -m "feat: agregar partial _detalle_alertas.html con tarjetas de alertas"
```

---

## Task 2: Crear infraestructura de tests

**Files:**
- Create: `gestion/tests/__init__.py`
- Create: `gestion/tests/test_dashboard.py`

- [ ] **Step 1: Crear el directorio y `__init__.py`**

Crear `gestion/tests/__init__.py` con contenido vacío.

- [ ] **Step 2: Escribir los tests**

Crear `gestion/tests/test_dashboard.py`:

```python
import json
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User


class DashboardLivianoTest(TestCase):
    """El dashboard solo hace 2 queries COUNT — no ejecuta cálculos de alertas."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser', password='testpass123'
        )
        self.client.login(username='testuser', password='testpass123')

    def test_dashboard_requiere_login(self):
        self.client.logout()
        response = self.client.get(reverse('gestion:dashboard'))
        self.assertNotEqual(response.status_code, 200)

    def test_dashboard_carga_correctamente(self):
        response = self.client.get(reverse('gestion:dashboard'))
        self.assertEqual(response.status_code, 200)

    def test_dashboard_context_solo_tiene_conteos_basicos(self):
        response = self.client.get(reverse('gestion:dashboard'))
        self.assertIn('total_contratos', response.context)
        self.assertIn('total_polizas', response.context)
        # NO debe tener alertas en el contexto — esas vienen por AJAX
        self.assertNotIn('contratos_por_vencer', response.context)
        self.assertNotIn('alertas_ipc', response.context)
        self.assertNotIn('polizas_criticas', response.context)

    def test_dashboard_usa_template_correcto(self):
        response = self.client.get(reverse('gestion:dashboard'))
        self.assertTemplateUsed(response, 'gestion/dashboard/index.html')


class CentroAlertasTest(TestCase):
    """La vista centro_alertas renderiza el contenedor sin calcular alertas."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser2', password='testpass123'
        )
        self.client.login(username='testuser2', password='testpass123')

    def test_centro_alertas_requiere_login(self):
        self.client.logout()
        response = self.client.get(reverse('gestion:centro_alertas'))
        self.assertNotEqual(response.status_code, 200)

    def test_centro_alertas_carga_correctamente(self):
        response = self.client.get(reverse('gestion:centro_alertas'))
        self.assertEqual(response.status_code, 200)

    def test_centro_alertas_usa_template_correcto(self):
        response = self.client.get(reverse('gestion:centro_alertas'))
        self.assertTemplateUsed(response, 'gestion/alertas/index.html')

    def test_centro_alertas_acepta_tipo_filtro(self):
        response = self.client.get(
            reverse('gestion:centro_alertas') + '?tipo_alerta=CLIENTE'
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['tipo_filtro'], 'CLIENTE')


class ApiConteosAlertasTest(TestCase):
    """El endpoint AJAX devuelve JSON con conteos y estadísticas."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser3', password='testpass123'
        )
        self.client.login(username='testuser3', password='testpass123')

    def test_requiere_login(self):
        self.client.logout()
        response = self.client.get(reverse('gestion:api_conteos_alertas'))
        self.assertEqual(response.status_code, 403)

    def test_devuelve_json(self):
        response = self.client.get(reverse('gestion:api_conteos_alertas'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')

    def test_estructura_json_correcta(self):
        response = self.client.get(reverse('gestion:api_conteos_alertas'))
        data = json.loads(response.content)
        self.assertIn('contratos_vigentes', data)
        self.assertIn('contratos_vencidos', data)
        self.assertIn('total_polizas', data)
        self.assertIn('contratos_fijos', data)
        self.assertIn('contratos_variables', data)
        self.assertIn('contratos_hibridos', data)
        self.assertIn('alertas', data)
        alertas = data['alertas']
        for key in ['vencimiento', 'polizas_criticas', 'preaviso', 'ipc',
                    'salario_minimo', 'polizas_requeridas', 'terminacion',
                    'renovacion_automatica']:
            self.assertIn(key, alertas)
            self.assertIsInstance(alertas[key], int)


class ApiDetalleAlertasTest(TestCase):
    """El endpoint AJAX devuelve HTML pre-renderizado con todas las alertas."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser4', password='testpass123'
        )
        self.client.login(username='testuser4', password='testpass123')

    def test_requiere_login(self):
        self.client.logout()
        response = self.client.get(reverse('gestion:api_detalle_alertas'))
        self.assertEqual(response.status_code, 403)

    def test_devuelve_json(self):
        response = self.client.get(reverse('gestion:api_detalle_alertas'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')

    def test_estructura_json_correcta(self):
        response = self.client.get(reverse('gestion:api_detalle_alertas'))
        data = json.loads(response.content)
        self.assertIn('html', data)
        self.assertIn('totales', data)
        self.assertIsInstance(data['html'], str)
        self.assertGreater(len(data['html']), 0)

    def test_acepta_filtro_tipo_alerta(self):
        response = self.client.get(
            reverse('gestion:api_detalle_alertas') + '?tipo_alerta=CLIENTE'
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertIn('html', data)
```

- [ ] **Step 3: Correr tests (deben FALLAR — las vistas no existen aún)**

```bash
cd "C:/Users/USER9/OneDrive - GLOBAL ANALITICS SAS/Proyecto_Contratos"
python manage.py test gestion.tests.test_dashboard -v 2
```

Resultado esperado: `ERROR` en varios tests — `NoReverseMatch` porque las URLs no existen todavía.

- [ ] **Step 4: Commit de los tests**

```bash
git add gestion/tests/__init__.py gestion/tests/test_dashboard.py
git commit -m "test: agregar tests para dashboard liviano, centro_alertas y endpoints AJAX"
```

---

## Task 3: Implementar los endpoints AJAX y `centro_alertas` en `dashboard.py`

**Files:**
- Modify: `gestion/views/dashboard.py`

Agregar al final del archivo `gestion/views/dashboard.py` (después de la función `dashboard` existente, antes de `exportaciones`):

- [ ] **Step 1: Agregar `centro_alertas` en `dashboard.py`**

Localizar la línea `@login_required_custom` que precede a `def exportaciones(request):` (aprox. línea 198) e insertar antes de ella:

```python
@login_required_custom
def centro_alertas(request):
    """
    Vista dedicada para el centro de alertas.
    Renderiza el contenedor vacío — las alertas se cargan vía AJAX.
    """
    tipo_filtro = request.GET.get('tipo_alerta', '')
    context = {
        'tipo_filtro': tipo_filtro,
        'fecha_actual': timezone.now().date(),
    }
    return render(request, 'gestion/alertas/index.html', context)


@login_required_custom
def api_conteos_alertas(request):
    """
    Endpoint AJAX: devuelve estadísticas generales + conteos de alertas.
    No devuelve el detalle — solo números para el panel de inicio.
    """
    from django.http import JsonResponse

    if not request.user.is_authenticated:
        return JsonResponse({'error': 'No autorizado'}, status=403)

    fecha_actual = timezone.now().date()

    # Stats generales (loop pesado movido aquí desde dashboard)
    todos_los_contratos = Contrato.objects.prefetch_related('otrosi', 'renovaciones_automaticas')
    contratos_vigentes = 0
    contratos_vencidos = 0
    contratos_vigentes_list = []

    for contrato in todos_los_contratos:
        if _estado_vigente_contrato(contrato, fecha_actual):
            contratos_vigentes += 1
            contratos_vigentes_list.append(contrato)
        else:
            contratos_vencidos += 1

    contratos_fijos = 0
    contratos_variables = 0
    contratos_hibridos = 0

    for contrato in contratos_vigentes_list:
        otrosi_modificador = get_ultimo_otrosi_que_modifico_campo_hasta_fecha(
            contrato, 'nueva_modalidad_pago', fecha_actual
        )
        if otrosi_modificador and otrosi_modificador.nueva_modalidad_pago:
            modalidad_actual = otrosi_modificador.nueva_modalidad_pago
        else:
            modalidad_actual = contrato.modalidad_pago

        if modalidad_actual == 'Fijo':
            contratos_fijos += 1
        elif modalidad_actual == 'Variable Puro':
            contratos_variables += 1
        elif modalidad_actual == 'Hibrido (Min Garantizado)':
            contratos_hibridos += 1

    # Conteos de alertas (solo len — sin objetos completos)
    vencimiento = len(obtener_alertas_expiracion_contratos(fecha_referencia=fecha_actual, ventana_dias=90))
    polizas_criticas = len(obtener_polizas_criticas(fecha_referencia=fecha_actual))
    preaviso = len(obtener_alertas_preaviso(fecha_referencia=fecha_actual))
    ipc_list = obtener_alertas_ipc(fecha_referencia=fecha_actual)
    sm_list = obtener_alertas_salario_minimo(fecha_referencia=fecha_actual)

    # Deduplicación IPC / Salario Mínimo (preservar lógica original)
    from gestion.services.alertas import obtener_tipo_condicion_ipc_vigente
    ids_en_sm = {a.contrato.id for a in sm_list}
    ids_en_ipc = {a.contrato.id for a in ipc_list}
    contratos_duplicados = ids_en_ipc & ids_en_sm
    if contratos_duplicados:
        ipc_list = [
            a for a in ipc_list
            if a.contrato.id not in contratos_duplicados
            or obtener_tipo_condicion_ipc_vigente(a.contrato, fecha_actual) == 'IPC'
        ]
        sm_list = [
            a for a in sm_list
            if a.contrato.id not in contratos_duplicados
            or obtener_tipo_condicion_ipc_vigente(a.contrato, fecha_actual) == 'SALARIO_MINIMO'
        ]

    polizas_requeridas = len(obtener_alertas_polizas_requeridas_no_aportadas(fecha_referencia=fecha_actual))
    terminacion = len(obtener_alertas_terminacion_anticipada(fecha_referencia=fecha_actual))
    renovacion_automatica = len(obtener_alertas_renovacion_automatica(fecha_referencia=fecha_actual))

    return JsonResponse({
        'contratos_vigentes': contratos_vigentes,
        'contratos_vencidos': contratos_vencidos,
        'total_polizas': Poliza.objects.count(),
        'contratos_fijos': contratos_fijos,
        'contratos_variables': contratos_variables,
        'contratos_hibridos': contratos_hibridos,
        'alertas': {
            'vencimiento': vencimiento,
            'polizas_criticas': polizas_criticas,
            'preaviso': preaviso,
            'ipc': len(ipc_list),
            'salario_minimo': len(sm_list),
            'polizas_requeridas': polizas_requeridas,
            'terminacion': terminacion,
            'renovacion_automatica': renovacion_automatica,
        },
    })


@login_required_custom
def api_detalle_alertas(request):
    """
    Endpoint AJAX: devuelve HTML pre-renderizado con todas las tarjetas de alertas.
    Acepta ?tipo_alerta=CLIENTE|PROVEEDOR para filtrar.
    """
    from django.http import JsonResponse
    from django.template.loader import render_to_string

    if not request.user.is_authenticated:
        return JsonResponse({'error': 'No autorizado'}, status=403)

    fecha_actual = timezone.now().date()
    tipo_filtro = request.GET.get('tipo_alerta', '')

    # === Lógica idéntica al dashboard original ===
    contratos_por_vencer_list = obtener_alertas_expiracion_contratos(fecha_referencia=fecha_actual, ventana_dias=90)
    contratos_por_vencer_con_fecha = []
    for contrato in contratos_por_vencer_list:
        if tipo_filtro and contrato.tipo_contrato_cliente_proveedor != tipo_filtro:
            continue
        fecha_final_actual = _obtener_fecha_final_contrato(contrato, fecha_actual)
        contratos_por_vencer_con_fecha.append({
            'contrato': contrato,
            'fecha_final_actualizada': fecha_final_actual,
        })

    polizas_criticas_list = obtener_polizas_criticas(fecha_referencia=fecha_actual)
    polizas_criticas = [
        p for p in polizas_criticas_list
        if not tipo_filtro or p.contrato.tipo_contrato_cliente_proveedor == tipo_filtro
    ]

    alertas_preaviso_list = obtener_alertas_preaviso(fecha_referencia=fecha_actual)
    alertas_preaviso_con_fecha = []
    for contrato in alertas_preaviso_list:
        if tipo_filtro and contrato.tipo_contrato_cliente_proveedor != tipo_filtro:
            continue
        fecha_final_actual = _obtener_fecha_final_contrato(contrato, fecha_actual)
        alertas_preaviso_con_fecha.append({
            'contrato': contrato,
            'fecha_final_actualizada': fecha_final_actual,
        })

    alertas_ipc_list = obtener_alertas_ipc(
        fecha_referencia=fecha_actual,
        tipo_contrato_cp=tipo_filtro if tipo_filtro else None
    )
    alertas_ipc = list(alertas_ipc_list)

    alertas_salario_minimo_list = obtener_alertas_salario_minimo(
        fecha_referencia=fecha_actual,
        tipo_contrato_cp=tipo_filtro if tipo_filtro else None
    )
    alertas_salario_minimo = list(alertas_salario_minimo_list)

    # Deduplicación IPC / Salario Mínimo (preservar lógica original)
    from gestion.services.alertas import obtener_tipo_condicion_ipc_vigente
    ids_en_sm = {a.contrato.id for a in alertas_salario_minimo}
    ids_en_ipc = {a.contrato.id for a in alertas_ipc}
    contratos_duplicados = ids_en_ipc & ids_en_sm
    if contratos_duplicados:
        alertas_ipc = [
            a for a in alertas_ipc
            if a.contrato.id not in contratos_duplicados
            or obtener_tipo_condicion_ipc_vigente(a.contrato, fecha_actual) == 'IPC'
        ]
        alertas_salario_minimo = [
            a for a in alertas_salario_minimo
            if a.contrato.id not in contratos_duplicados
            or obtener_tipo_condicion_ipc_vigente(a.contrato, fecha_actual) == 'SALARIO_MINIMO'
        ]

    alertas_polizas_requeridas_list = obtener_alertas_polizas_requeridas_no_aportadas(fecha_referencia=fecha_actual)
    alertas_polizas_requeridas = [
        a for a in alertas_polizas_requeridas_list
        if not tipo_filtro or a.contrato.tipo_contrato_cliente_proveedor == tipo_filtro
    ]

    alertas_terminacion_list = obtener_alertas_terminacion_anticipada(fecha_referencia=fecha_actual)
    alertas_terminacion = [
        a for a in alertas_terminacion_list
        if not tipo_filtro or a.contrato.tipo_contrato_cliente_proveedor == tipo_filtro
    ]

    alertas_renovacion_automatica = obtener_alertas_renovacion_automatica(fecha_referencia=fecha_actual)

    context = {
        'fecha_actual': fecha_actual,
        'tipo_filtro': tipo_filtro,
        'contratos_por_vencer': contratos_por_vencer_con_fecha,
        'total_alertas_vencimiento': len(contratos_por_vencer_con_fecha),
        'polizas_criticas': polizas_criticas,
        'total_polizas_criticas': len(polizas_criticas),
        'hay_polizas_con_colchon': any(getattr(p, 'tiene_colchon', False) for p in polizas_criticas),
        'alertas_preaviso_renovacion': alertas_preaviso_con_fecha,
        'total_alertas_preaviso': len(alertas_preaviso_con_fecha),
        'alertas_ipc': alertas_ipc,
        'total_alertas_ipc': len(alertas_ipc),
        'alertas_salario_minimo': alertas_salario_minimo,
        'total_alertas_salario_minimo': len(alertas_salario_minimo),
        'alertas_polizas_requeridas': alertas_polizas_requeridas,
        'total_alertas_polizas_requeridas': len(alertas_polizas_requeridas),
        'alertas_terminacion': alertas_terminacion,
        'total_alertas_terminacion': len(alertas_terminacion),
        'alertas_renovacion_automatica': alertas_renovacion_automatica,
        'total_alertas_renovacion_automatica': len(alertas_renovacion_automatica),
    }

    html = render_to_string(
        'gestion/alertas/_detalle_alertas.html',
        context,
        request=request,
    )

    totales = {
        'vencimiento': len(contratos_por_vencer_con_fecha),
        'polizas_criticas': len(polizas_criticas),
        'preaviso': len(alertas_preaviso_con_fecha),
        'ipc': len(alertas_ipc),
        'salario_minimo': len(alertas_salario_minimo),
        'polizas_requeridas': len(alertas_polizas_requeridas),
        'terminacion': len(alertas_terminacion),
        'renovacion_automatica': len(alertas_renovacion_automatica),
    }

    return JsonResponse({'html': html, 'totales': totales})
```

- [ ] **Step 2: Commit de las nuevas vistas**

```bash
git add gestion/views/dashboard.py
git commit -m "feat: agregar centro_alertas, api_conteos_alertas y api_detalle_alertas"
```

---

## Task 4: Registrar las nuevas vistas en `__init__.py` y `urls.py`

**Files:**
- Modify: `gestion/views/__init__.py`
- Modify: `gestion/urls.py`

- [ ] **Step 1: Agregar imports en `gestion/views/__init__.py`**

En la línea 1 del archivo, la importación desde `dashboard` actualmente es:

```python
from gestion.views.dashboard import (
    dashboard,
    exportaciones,
    exportar_alertas_ipc,
    exportar_alertas_salario_minimo,
    exportar_alertas_vencimiento,
    exportar_alertas_polizas,
    exportar_alertas_preaviso,
    exportar_alertas_polizas_requeridas,
    exportar_alertas_terminacion,
    exportar_terceros,
    exportar_locales,
    exportar_recobro_polizas,
)
```

Reemplazarla por:

```python
from gestion.views.dashboard import (
    dashboard,
    centro_alertas,
    api_conteos_alertas,
    api_detalle_alertas,
    exportaciones,
    exportar_alertas_ipc,
    exportar_alertas_salario_minimo,
    exportar_alertas_vencimiento,
    exportar_alertas_polizas,
    exportar_alertas_preaviso,
    exportar_alertas_polizas_requeridas,
    exportar_alertas_terminacion,
    exportar_terceros,
    exportar_locales,
    exportar_recobro_polizas,
)
```

- [ ] **Step 2: Agregar al `__all__` en `gestion/views/__init__.py`**

Localizar la línea `'dashboard',` dentro de `__all__` y agregar las tres nuevas entradas justo debajo:

```python
    'dashboard',
    'centro_alertas',
    'api_conteos_alertas',
    'api_detalle_alertas',
```

- [ ] **Step 3: Agregar URLs en `gestion/urls.py`**

Localizar la primera URL `path('', views.dashboard, name='dashboard'),` y agregar las tres nuevas rutas inmediatamente después:

```python
    path('', views.dashboard, name='dashboard'),
    path('alertas/', views.centro_alertas, name='centro_alertas'),
    path('api/conteos-alertas/', views.api_conteos_alertas, name='api_conteos_alertas'),
    path('api/detalle-alertas/', views.api_detalle_alertas, name='api_detalle_alertas'),
```

- [ ] **Step 4: Correr los tests — ahora deben pasar**

```bash
cd "C:/Users/USER9/OneDrive - GLOBAL ANALITICS SAS/Proyecto_Contratos"
python manage.py test gestion.tests.test_dashboard -v 2
```

Resultado esperado: todos los tests en `PASS`. Si alguno falla, revisar el error antes de continuar.

- [ ] **Step 5: Commit**

```bash
git add gestion/views/__init__.py gestion/urls.py
git commit -m "feat: registrar centro_alertas y endpoints AJAX en views/__init__.py y urls.py"
```

---

## Task 5: Refactorizar `dashboard()` para que sea liviano

**Files:**
- Modify: `gestion/views/dashboard.py`

La función `dashboard()` actual (líneas 31-195) ejecuta 8 cálculos de alertas + el loop de vigentes/modalidades. Debe quedar únicamente con 2 queries COUNT.

- [ ] **Step 1: Reemplazar el cuerpo de `dashboard()`**

Reemplazar completamente la función `dashboard()` actual por:

```python
@login_required_custom
def dashboard(request):
    """
    Dashboard principal — carga instantánea.
    Solo realiza 2 queries COUNT. Las estadísticas pesadas y las alertas
    se cargan vía AJAX por api_conteos_alertas() y api_detalle_alertas().
    """
    context = {
        'total_contratos': Contrato.objects.count(),
        'total_polizas': Poliza.objects.count(),
        'fecha_actual': timezone.now().date(),
    }
    return render(request, 'gestion/dashboard/index.html', context)
```

Los imports de `obtener_alertas_*` al inicio del archivo se mantienen porque los usan los nuevos endpoints AJAX.

- [ ] **Step 2: Correr los tests para confirmar que siguen pasando**

```bash
cd "C:/Users/USER9/OneDrive - GLOBAL ANALITICS SAS/Proyecto_Contratos"
python manage.py test gestion.tests.test_dashboard -v 2
```

Resultado esperado: todos los tests en `PASS`.

- [ ] **Step 3: Commit**

```bash
git add gestion/views/dashboard.py
git commit -m "perf: refactorizar dashboard() a 2 queries COUNT — stats y alertas se cargan vía AJAX"
```

---

## Task 6: Actualizar el template `templates/gestion/dashboard/index.html`

**Files:**
- Modify: `templates/gestion/dashboard/index.html`

El template actual tiene ~880 líneas. Se reemplaza completamente con la versión liviana.

- [ ] **Step 1: Reemplazar `templates/gestion/dashboard/index.html`**

```html
{% extends 'base.html' %}

{% block title %}Inicio - Gestión de Contratos{% endblock %}

{% block content %}
<div class="container-fluid">

    <!-- Header -->
    <div class="row mb-4">
        <div class="col-12">
            <div class="d-flex justify-content-between align-items-center">
                <h1 class="display-4 mb-0">
                    <i class="fas fa-tachometer-alt text-primary"></i> Inicio
                </h1>
                <div class="btn-group" role="group">
                    <a href="{% url 'gestion:nuevo_contrato' %}" class="btn btn-primary">
                        <i class="fas fa-plus"></i> Nuevo Contrato
                    </a>
                    <a href="{% url 'gestion:lista_contratos' %}" class="btn btn-outline-primary">
                        <i class="fas fa-list"></i> Ver Todos
                    </a>
                </div>
            </div>
        </div>
    </div>

    <!-- Estadísticas generales — carga síncrona (solo COUNTs) -->
    <div class="row mb-4">
        <div class="col-md-3 mb-3">
            <div class="card stat-card text-center">
                <div class="card-body">
                    <h3>{{ total_contratos }}</h3>
                    <p class="mb-0">Total Contratos</p>
                </div>
            </div>
        </div>
        <div class="col-md-3 mb-3">
            <div class="card stat-card-alt text-center">
                <div class="card-body">
                    <h3 id="stat-vigentes">
                        <span class="spinner-border spinner-border-sm text-light" role="status" aria-hidden="true"></span>
                    </h3>
                    <p class="mb-0">Contratos Vigentes</p>
                </div>
            </div>
        </div>
        <div class="col-md-3 mb-3">
            <div class="card stat-card text-center">
                <div class="card-body">
                    <h3 id="stat-vencidos">
                        <span class="spinner-border spinner-border-sm text-light" role="status" aria-hidden="true"></span>
                    </h3>
                    <p class="mb-0">Contratos Vencidos</p>
                </div>
            </div>
        </div>
        <div class="col-md-3 mb-3">
            <div class="card stat-card-alt text-center">
                <div class="card-body">
                    <h3>{{ total_polizas }}</h3>
                    <p class="mb-0">Total Pólizas</p>
                </div>
            </div>
        </div>
    </div>

    <!-- Distribución por Modalidad — carga AJAX -->
    <div class="row mb-4">
        <div class="col-12">
            <div class="card">
                <div class="card-header">
                    <h5 class="mb-0">
                        <i class="fas fa-chart-pie text-info"></i> Distribución por Modalidad de Pago (vigentes)
                    </h5>
                </div>
                <div class="card-body">
                    <div class="row">
                        <div class="col-md-4 text-center">
                            <div class="border rounded p-3" style="border-color: var(--avenida-orange) !important;">
                                <h4 class="text-primary" id="stat-fijos">
                                    <span class="spinner-border spinner-border-sm" role="status"></span>
                                </h4>
                                <p class="mb-0">Contratos Fijos</p>
                            </div>
                        </div>
                        <div class="col-md-4 text-center">
                            <div class="border rounded p-3" style="border-color: var(--avenida-green) !important;">
                                <h4 class="text-success" id="stat-variables">
                                    <span class="spinner-border spinner-border-sm" role="status"></span>
                                </h4>
                                <p class="mb-0">Contratos Variables</p>
                            </div>
                        </div>
                        <div class="col-md-4 text-center">
                            <div class="border rounded p-3" style="border-color: var(--avenida-cyan) !important;">
                                <h4 class="text-info" id="stat-hibridos">
                                    <span class="spinner-border spinner-border-sm" role="status"></span>
                                </h4>
                                <p class="mb-0">Contratos Híbridos</p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- Acciones Rápidas -->
    <div class="row mb-4">
        <div class="col-12">
            <div class="card">
                <div class="card-header">
                    <h5 class="mb-0">
                        <i class="fas fa-bolt text-warning"></i> Acciones Rápidas
                    </h5>
                </div>
                <div class="card-body">
                    <div class="row">
                        <div class="col-md-3 mb-3">
                            <a href="{% url 'gestion:nuevo_contrato' %}" class="btn btn-primary w-100">
                                <i class="fas fa-plus fa-2x mb-2"></i><br>Nuevo Contrato
                            </a>
                        </div>
                        <div class="col-md-3 mb-3">
                            {% url 'gestion:dashboard' as dashboard_url %}
                            <a href="{% url 'gestion:nuevo_arrendatario' %}?next={{ dashboard_url|urlencode }}" class="btn btn-success w-100">
                                <i class="fas fa-users fa-2x mb-2"></i><br>Nuevo Tercero
                            </a>
                            <a href="{% url 'gestion:lista_arrendatarios' %}" class="btn btn-sm btn-outline-success w-100 mt-2">
                                <i class="fas fa-list"></i> Listar Terceros
                            </a>
                        </div>
                        <div class="col-md-3 mb-3">
                            {% url 'gestion:dashboard' as dashboard_url %}
                            <a href="{% url 'gestion:nuevo_local' %}?next={{ dashboard_url|urlencode }}" class="btn btn-info w-100">
                                <i class="fas fa-store fa-2x mb-2"></i><br>Nuevo Local
                            </a>
                            <a href="{% url 'gestion:lista_locales' %}" class="btn btn-sm btn-outline-info w-100 mt-2">
                                <i class="fas fa-list"></i> Listar Locales
                            </a>
                        </div>
                        <div class="col-md-3 mb-3">
                            <a href="{% url 'gestion:exportaciones' %}" class="btn btn-warning w-100">
                                <i class="fas fa-file-export fa-2x mb-2"></i><br>Exportaciones
                            </a>
                        </div>
                        <div class="col-md-3 mb-3">
                            <a href="{% url 'gestion:lista_contratos' %}" class="btn btn-primary w-100" style="background-color: #2196F3; border-color: #2196F3;">
                                <i class="fas fa-list fa-2x mb-2"></i><br>Ver Contratos
                            </a>
                        </div>
                        <div class="col-md-3 mb-3">
                            <a href="{% url 'gestion:lista_informes_ventas' %}" class="btn btn-primary w-100" style="background-color: var(--avenida-green); border-color: var(--avenida-green);">
                                <i class="fas fa-chart-line fa-2x mb-2"></i><br>Informes de Ventas
                            </a>
                        </div>
                        <div class="col-md-3 mb-3">
                            <a href="{% url 'gestion:lista_ipc_historico' %}" class="btn btn-primary w-100" style="background-color: var(--avenida-cyan); border-color: var(--avenida-cyan);">
                                <i class="fas fa-percentage fa-2x mb-2"></i><br>Gestión IPC
                            </a>
                        </div>
                        <div class="col-md-3 mb-3">
                            <a href="{% url 'gestion:gestion_renovaciones_automaticas' %}" class="btn btn-primary w-100" style="background-color: var(--avenida-orange); border-color: var(--avenida-orange);">
                                <i class="fas fa-sync-alt fa-2x mb-2"></i><br>Renovaciones Automáticas
                                <span id="badge-renovacion" class="badge bg-danger ms-2" style="display:none;"></span>
                            </a>
                        </div>
                        <div class="col-md-3 mb-3">
                            <a href="{% url 'gestion:gestionar_clausulas' %}" class="btn btn-primary w-100" style="background-color: var(--avenida-magenta); border-color: var(--avenida-magenta);">
                                <i class="fas fa-file-contract fa-2x mb-2"></i><br>Gestionar Cláusulas
                            </a>
                            <a href="{% url 'gestion:parametrizar_clausulas' %}" class="btn btn-sm btn-outline-secondary w-100 mt-2">
                                <i class="fas fa-cog"></i> Parametrizar
                            </a>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- Panel Estado de Alertas — conteos cargados vía AJAX -->
    <div class="row mb-4">
        <div class="col-12">
            <div class="card">
                <div class="card-header d-flex justify-content-between align-items-center">
                    <h5 class="mb-0">
                        <i class="fas fa-bell text-warning"></i> Estado de Alertas
                    </h5>
                    <a href="{% url 'gestion:centro_alertas' %}" class="btn btn-primary btn-sm">
                        <i class="fas fa-external-link-alt"></i> Ver Centro de Alertas
                    </a>
                </div>
                <div class="card-body">
                    <div id="alertas-error" class="alert alert-warning d-none">
                        <i class="fas fa-exclamation-triangle"></i>
                        No se pudieron cargar los conteos de alertas.
                        <button class="btn btn-sm btn-outline-warning ms-2" onclick="cargarConteos()">Reintentar</button>
                    </div>
                    <div class="row" id="alertas-conteos">
                        <!-- Vencimiento -->
                        <div class="col-6 col-md-3 mb-3">
                            <div class="border rounded p-3 text-center h-100" style="border-color: var(--avenida-orange)!important;">
                                <div class="mb-1">
                                    <i class="fas fa-exclamation-triangle" style="color: var(--avenida-orange);"></i>
                                </div>
                                <h4 id="cnt-vencimiento" class="mb-1">
                                    <span class="spinner-border spinner-border-sm" role="status"></span>
                                </h4>
                                <small class="text-muted">Vencimiento</small>
                            </div>
                        </div>
                        <!-- Pólizas Críticas -->
                        <div class="col-6 col-md-3 mb-3">
                            <div class="border rounded p-3 text-center h-100" style="border-color: var(--avenida-magenta)!important;">
                                <div class="mb-1">
                                    <i class="fas fa-shield-alt" style="color: var(--avenida-magenta);"></i>
                                </div>
                                <h4 id="cnt-polizas" class="mb-1">
                                    <span class="spinner-border spinner-border-sm" role="status"></span>
                                </h4>
                                <small class="text-muted">Pólizas Críticas</small>
                            </div>
                        </div>
                        <!-- Preaviso -->
                        <div class="col-6 col-md-3 mb-3">
                            <div class="border rounded p-3 text-center h-100" style="border-color: var(--avenida-cyan)!important;">
                                <div class="mb-1">
                                    <i class="fas fa-clock" style="color: var(--avenida-cyan);"></i>
                                </div>
                                <h4 id="cnt-preaviso" class="mb-1">
                                    <span class="spinner-border spinner-border-sm" role="status"></span>
                                </h4>
                                <small class="text-muted">Preaviso</small>
                            </div>
                        </div>
                        <!-- IPC -->
                        <div class="col-6 col-md-3 mb-3">
                            <div class="border rounded p-3 text-center h-100" style="border-color: var(--avenida-green)!important;">
                                <div class="mb-1">
                                    <i class="fas fa-percentage" style="color: var(--avenida-green);"></i>
                                </div>
                                <h4 id="cnt-ipc" class="mb-1">
                                    <span class="spinner-border spinner-border-sm" role="status"></span>
                                </h4>
                                <small class="text-muted">Ajuste IPC</small>
                            </div>
                        </div>
                        <!-- Salario Mínimo -->
                        <div class="col-6 col-md-3 mb-3">
                            <div class="border rounded p-3 text-center h-100" style="border-color: #28a745!important;">
                                <div class="mb-1">
                                    <i class="fas fa-dollar-sign" style="color: #28a745;"></i>
                                </div>
                                <h4 id="cnt-salario" class="mb-1">
                                    <span class="spinner-border spinner-border-sm" role="status"></span>
                                </h4>
                                <small class="text-muted">Salario Mínimo</small>
                            </div>
                        </div>
                        <!-- Pólizas Requeridas -->
                        <div class="col-6 col-md-3 mb-3">
                            <div class="border rounded p-3 text-center h-100" style="border-color: var(--avenida-magenta)!important;">
                                <div class="mb-1">
                                    <i class="fas fa-exclamation-circle" style="color: var(--avenida-magenta);"></i>
                                </div>
                                <h4 id="cnt-polizas-req" class="mb-1">
                                    <span class="spinner-border spinner-border-sm" role="status"></span>
                                </h4>
                                <small class="text-muted">Pólizas Requeridas</small>
                            </div>
                        </div>
                        <!-- Terminación Anticipada -->
                        <div class="col-6 col-md-3 mb-3">
                            <div class="border rounded p-3 text-center h-100" style="border-color: var(--avenida-orange)!important;">
                                <div class="mb-1">
                                    <i class="fas fa-hourglass-half" style="color: var(--avenida-orange);"></i>
                                </div>
                                <h4 id="cnt-terminacion" class="mb-1">
                                    <span class="spinner-border spinner-border-sm" role="status"></span>
                                </h4>
                                <small class="text-muted">Terminación</small>
                            </div>
                        </div>
                        <!-- Renovación Automática -->
                        <div class="col-6 col-md-3 mb-3">
                            <div class="border rounded p-3 text-center h-100" style="border-color: var(--avenida-orange)!important;">
                                <div class="mb-1">
                                    <i class="fas fa-sync-alt" style="color: var(--avenida-orange);"></i>
                                </div>
                                <h4 id="cnt-renovacion" class="mb-1">
                                    <span class="spinner-border spinner-border-sm" role="status"></span>
                                </h4>
                                <small class="text-muted">Renovación Auto.</small>
                            </div>
                        </div>
                    </div>
                    <div class="text-center mt-2">
                        <small class="text-muted">
                            <i class="fas fa-info-circle"></i>
                            Los conteos se cargan en segundo plano. Para ver el detalle completo, use
                            <a href="{% url 'gestion:centro_alertas' %}">Centro de Alertas</a>.
                        </small>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- Footer -->
    <div class="row">
        <div class="col-12">
            <div class="card">
                <div class="card-body text-center text-muted">
                    <small>
                        <i class="fas fa-info-circle"></i>
                        Fecha actual: {{ fecha_actual }} |
                        <a href="/admin/" class="text-decoration-none">Ir a Administración</a>
                    </small>
                </div>
            </div>
        </div>
    </div>

</div>
{% endblock %}

{% block extra_js %}
<script>
function setConteo(id, valor) {
    const el = document.getElementById(id);
    if (!el) return;
    const color = valor > 0 ? 'color: #dc3545; font-weight: bold;' : 'color: var(--avenida-green);';
    el.innerHTML = '<span style="' + color + '">' + valor + '</span>';
}

function cargarConteos() {
    document.getElementById('alertas-error').classList.add('d-none');

    fetch('{% url "gestion:api_conteos_alertas" %}', {
        headers: {'X-Requested-With': 'XMLHttpRequest'}
    })
    .then(function(response) {
        if (!response.ok) throw new Error('Error ' + response.status);
        return response.json();
    })
    .then(function(data) {
        // Stats de modalidades
        document.getElementById('stat-vigentes').textContent = data.contratos_vigentes;
        document.getElementById('stat-vencidos').textContent = data.contratos_vencidos;
        document.getElementById('stat-fijos').textContent = data.contratos_fijos;
        document.getElementById('stat-variables').textContent = data.contratos_variables;
        document.getElementById('stat-hibridos').textContent = data.contratos_hibridos;

        // Conteos de alertas
        var a = data.alertas;
        setConteo('cnt-vencimiento', a.vencimiento);
        setConteo('cnt-polizas', a.polizas_criticas);
        setConteo('cnt-preaviso', a.preaviso);
        setConteo('cnt-ipc', a.ipc);
        setConteo('cnt-salario', a.salario_minimo);
        setConteo('cnt-polizas-req', a.polizas_requeridas);
        setConteo('cnt-terminacion', a.terminacion);
        setConteo('cnt-renovacion', a.renovacion_automatica);

        // Badge de renovación en acciones rápidas
        var badge = document.getElementById('badge-renovacion');
        if (badge && a.renovacion_automatica > 0) {
            badge.textContent = a.renovacion_automatica;
            badge.style.display = '';
        }
    })
    .catch(function() {
        document.getElementById('alertas-error').classList.remove('d-none');
        // Limpiar spinners en error
        ['cnt-vencimiento','cnt-polizas','cnt-preaviso','cnt-ipc',
         'cnt-salario','cnt-polizas-req','cnt-terminacion','cnt-renovacion'].forEach(function(id) {
            var el = document.getElementById(id);
            if (el) el.innerHTML = '<small class="text-muted">-</small>';
        });
        ['stat-vigentes','stat-vencidos','stat-fijos','stat-variables','stat-hibridos'].forEach(function(id) {
            var el = document.getElementById(id);
            if (el) el.innerHTML = '<small class="text-muted">-</small>';
        });
    });
}

document.addEventListener('DOMContentLoaded', cargarConteos);
</script>
{% endblock %}
```

- [ ] **Step 2: Correr los tests para confirmar que siguen pasando**

```bash
cd "C:/Users/USER9/OneDrive - GLOBAL ANALITICS SAS/Proyecto_Contratos"
python manage.py test gestion.tests.test_dashboard -v 2
```

Resultado esperado: todos en `PASS`.

- [ ] **Step 3: Commit**

```bash
git add templates/gestion/dashboard/index.html
git commit -m "feat: refactorizar template de inicio — estadísticas y alertas via AJAX"
```

---

## Task 7: Crear el template `templates/gestion/alertas/index.html`

**Files:**
- Create: `templates/gestion/alertas/index.html`

- [ ] **Step 1: Crear el template del centro de alertas**

```html
{% extends 'base.html' %}

{% block title %}Centro de Alertas - Gestión de Contratos{% endblock %}

{% block content %}
<div class="container-fluid">

    <!-- Header -->
    <div class="row mb-4">
        <div class="col-12">
            <div class="d-flex justify-content-between align-items-center flex-wrap gap-2">
                <h1 class="display-4 mb-0">
                    <i class="fas fa-bell text-primary"></i> Centro de Alertas
                </h1>
                <a href="{% url 'gestion:dashboard' %}" class="btn btn-volver-inicio">
                    <i class="fas fa-home"></i> Volver al Inicio
                </a>
            </div>
        </div>
    </div>

    <!-- Filtro Global -->
    <div class="row mb-3">
        <div class="col-12">
            <div class="card">
                <div class="card-body py-2">
                    <div class="d-flex align-items-center">
                        <span class="me-3"><strong>Filtrar Alertas:</strong></span>
                        <div class="btn-group" role="group">
                            <button
                                type="button"
                                class="btn btn-sm {% if not tipo_filtro %}btn-primary{% else %}btn-outline-primary{% endif %}"
                                onclick="cargarAlertas('')"
                            >Todos</button>
                            <button
                                type="button"
                                class="btn btn-sm {% if tipo_filtro == 'CLIENTE' %}btn-primary{% else %}btn-outline-primary{% endif %}"
                                onclick="cargarAlertas('CLIENTE')"
                            >Clientes</button>
                            <button
                                type="button"
                                class="btn btn-sm {% if tipo_filtro == 'PROVEEDOR' %}btn-primary{% else %}btn-outline-primary{% endif %}"
                                onclick="cargarAlertas('PROVEEDOR')"
                            >Proveedores</button>
                        </div>
                        <span class="ms-3 text-muted small" id="filtro-activo">
                            {% if tipo_filtro %}Mostrando: {{ tipo_filtro|capfirst|lower }}s{% else %}Mostrando: todos{% endif %}
                        </span>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- Panel de progreso (visible mientras carga) -->
    <div id="panel-carga" class="row mb-4">
        <div class="col-12">
            <div class="card border-0 shadow-sm">
                <div class="card-body py-4 text-center">
                    <div class="mb-3">
                        <i class="fas fa-cogs fa-3x" style="color: var(--avenida-orange); animation: fa-spin 2s linear infinite;"></i>
                    </div>
                    <h5 class="mb-3" id="msg-progreso">Iniciando cálculo de alertas...</h5>
                    <div class="progress mb-2" style="height: 12px; max-width: 480px; margin: 0 auto;">
                        <div
                            id="barra-progreso"
                            class="progress-bar progress-bar-striped progress-bar-animated"
                            role="progressbar"
                            style="width: 0%; background-color: var(--avenida-orange);"
                        ></div>
                    </div>
                    <small class="text-muted">Esto puede tardar un momento según el volumen de contratos</small>
                </div>
            </div>
        </div>
    </div>

    <!-- Mensaje de error (oculto por defecto) -->
    <div id="panel-error" class="row mb-4 d-none">
        <div class="col-12">
            <div class="alert alert-danger d-flex align-items-center gap-3">
                <i class="fas fa-exclamation-circle fa-2x"></i>
                <div>
                    <strong>No se pudieron cargar las alertas.</strong>
                    <span id="msg-error" class="ms-1"></span>
                </div>
                <button class="btn btn-outline-danger btn-sm ms-auto" onclick="cargarAlertas(tipoFiltroActual)">
                    <i class="fas fa-redo"></i> Reintentar
                </button>
            </div>
        </div>
    </div>

    <!-- Contenido de alertas (oculto hasta que llegue el AJAX) -->
    <div id="contenido-alertas" class="d-none">
    </div>

    <!-- Footer -->
    <div class="row mt-2">
        <div class="col-12">
            <div class="card">
                <div class="card-body text-center text-muted">
                    <small>
                        <i class="fas fa-info-circle"></i>
                        Fecha de cálculo: {{ fecha_actual }} |
                        <a href="{% url 'gestion:exportaciones' %}" class="text-decoration-none">Exportaciones</a>
                    </small>
                </div>
            </div>
        </div>
    </div>

</div>
{% endblock %}

{% block extra_js %}
<script>
var tipoFiltroActual = '{{ tipo_filtro|escapejs }}';

var mensajesProgreso = [
    'Revisando vencimientos de contratos...',
    'Verificando estado de pólizas...',
    'Calculando alertas de ajuste de IPC...',
    'Revisando alertas de Salario Mínimo...',
    'Verificando pólizas requeridas no aportadas...',
    'Calculando períodos de terminación anticipada...',
    'Verificando renovaciones automáticas...',
    'Finalizando cálculos...',
];

var intervaloMensajes = null;
var indMensaje = 0;
var progresoActual = 5;

function iniciarProgreso() {
    var barra = document.getElementById('barra-progreso');
    var msg = document.getElementById('msg-progreso');
    if (barra) barra.style.width = '5%';
    if (msg) msg.textContent = mensajesProgreso[0];
    indMensaje = 0;
    progresoActual = 5;

    intervaloMensajes = setInterval(function() {
        indMensaje = (indMensaje + 1) % mensajesProgreso.length;
        if (msg) msg.textContent = mensajesProgreso[indMensaje];
        // Avanzar barra hasta máx 90% (el 100% lo hace la respuesta)
        progresoActual = Math.min(progresoActual + 10, 90);
        if (barra) barra.style.width = progresoActual + '%';
    }, 1500);
}

function detenerProgreso() {
    if (intervaloMensajes) {
        clearInterval(intervaloMensajes);
        intervaloMensajes = null;
    }
}

function completarProgreso(callback) {
    var barra = document.getElementById('barra-progreso');
    var msg = document.getElementById('msg-progreso');
    if (barra) barra.style.width = '100%';
    if (msg) msg.textContent = 'Listo.';
    setTimeout(function() {
        if (callback) callback();
    }, 400);
}

function mostrarError(mensaje) {
    detenerProgreso();
    document.getElementById('panel-carga').classList.add('d-none');
    document.getElementById('contenido-alertas').classList.add('d-none');
    var panelError = document.getElementById('panel-error');
    panelError.classList.remove('d-none');
    var msgError = document.getElementById('msg-error');
    if (msgError) msgError.textContent = mensaje || '';
}

function cargarAlertas(tipo) {
    tipoFiltroActual = tipo;

    // Actualizar estado visual del filtro
    var textoFiltro = document.getElementById('filtro-activo');
    if (textoFiltro) {
        textoFiltro.textContent = tipo ? 'Mostrando: ' + tipo.toLowerCase() + 's' : 'Mostrando: todos';
    }
    // Actualizar botones de filtro
    document.querySelectorAll('.btn-group .btn').forEach(function(btn) {
        btn.classList.remove('btn-primary');
        btn.classList.add('btn-outline-primary');
    });
    var btns = document.querySelectorAll('.btn-group .btn');
    if (tipo === '') btns[0] && btns[0].classList.replace('btn-outline-primary', 'btn-primary');
    if (tipo === 'CLIENTE') btns[1] && btns[1].classList.replace('btn-outline-primary', 'btn-primary');
    if (tipo === 'PROVEEDOR') btns[2] && btns[2].classList.replace('btn-outline-primary', 'btn-primary');

    // Mostrar panel de carga
    document.getElementById('panel-error').classList.add('d-none');
    document.getElementById('contenido-alertas').classList.add('d-none');
    document.getElementById('panel-carga').classList.remove('d-none');

    iniciarProgreso();

    var url = '{% url "gestion:api_detalle_alertas" %}';
    if (tipo) url += '?tipo_alerta=' + encodeURIComponent(tipo);

    fetch(url, {
        headers: {'X-Requested-With': 'XMLHttpRequest'}
    })
    .then(function(response) {
        if (response.status === 403) throw new Error('Sin autorización. Recargue la página.');
        if (!response.ok) throw new Error('Error del servidor (' + response.status + ').');
        return response.json();
    })
    .then(function(data) {
        detenerProgreso();
        completarProgreso(function() {
            var contenido = document.getElementById('contenido-alertas');
            contenido.innerHTML = data.html;
            document.getElementById('panel-carga').classList.add('d-none');
            contenido.classList.remove('d-none');
            // Re-inicializar el JS de toggle-alert que viene dentro del HTML insertado
            // (el script tag en el partial se ejecuta automáticamente al insertar innerHTML)
        });
    })
    .catch(function(err) {
        mostrarError(err.message);
    });
}

document.addEventListener('DOMContentLoaded', function() {
    cargarAlertas(tipoFiltroActual);
});
</script>
{% endblock %}
```

- [ ] **Step 2: Correr los tests**

```bash
cd "C:/Users/USER9/OneDrive - GLOBAL ANALITICS SAS/Proyecto_Contratos"
python manage.py test gestion.tests.test_dashboard -v 2
```

Resultado esperado: todos en `PASS`.

- [ ] **Step 3: Commit**

```bash
git add templates/gestion/alertas/index.html
git commit -m "feat: agregar template Centro de Alertas con barra de progreso y carga AJAX"
```

---

## Task 8: Verificación manual final

- [ ] **Step 1: Arrancar el servidor de desarrollo**

```bash
cd "C:/Users/USER9/OneDrive - GLOBAL ANALITICS SAS/Proyecto_Contratos"
python manage.py runserver
```

- [ ] **Step 2: Verificar el dashboard de inicio**

Navegar a `http://127.0.0.1:8000/`. Verificar:
- La página carga instantáneamente (sin demora perceptible)
- Se ven los spinners en "Contratos Vigentes", "Vencidos", "Fijos", "Variables", "Híbridos" y en los 8 contadores de alertas
- Después de unos segundos, los spinners se reemplazan por números reales
- El botón "Ver Centro de Alertas" está visible

- [ ] **Step 3: Verificar el centro de alertas**

Navegar a `http://127.0.0.1:8000/alertas/`. Verificar:
- La página carga de inmediato con el panel de progreso
- La barra de progreso avanza y los mensajes rotan
- Las tarjetas de alertas aparecen cuando termina la carga
- El filtro Todos / Clientes / Proveedores funciona (recarga las tarjetas con spinner)
- "Ver más / Ver menos" funciona en las tarjetas

- [ ] **Step 4: Verificar que la autenticación protege los endpoints AJAX**

```bash
curl http://127.0.0.1:8000/api/conteos-alertas/
```

Resultado esperado: redirección o respuesta de error (no JSON con datos).

- [ ] **Step 5: Correr suite de tests completa**

```bash
cd "C:/Users/USER9/OneDrive - GLOBAL ANALITICS SAS/Proyecto_Contratos"
python manage.py test gestion.tests -v 2
```

Resultado esperado: todos en `PASS`, sin errores.

- [ ] **Step 6: Commit final**

```bash
git add -A
git commit -m "feat: refactorización completa — dashboard liviano + Centro de Alertas con carga AJAX"
```

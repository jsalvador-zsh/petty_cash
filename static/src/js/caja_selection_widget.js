/** @odoo-module **/

import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

export class CajaSelectionWidget extends Component {
    static template = "petty_cash.CajaSelectionWidget";
    static props = {};

    setup() {
        this.actionService = useService("action");
        this.notification = useService("notification");
        this.orm = useService("orm");
        
        this.state = useState({
            showSelection: true,
            selectedType: null,
            stats: {
                petty_cash: { total: 0, open: 0, closed: 0, balance: 0 },
                distribution_cash: { total: 0, open: 0, closed: 0, balance: 0 },
                logistics_cash: { total: 0, open: 0, closed: 0, balance: 0 }
            }
        });

        onWillStart(async () => {
            await this.loadStats();
        });
    }

    /**
     * Obtener el ID del usuario actual
     */
    async getCurrentUserId() {
        try {
            const result = await this.orm.call("res.users", "search_read", [
                [["id", "=", this.env.services.user.userId || this.env.user.userId]],
                ["id"]
            ]);
            return result[0]?.id || null;
        } catch (error) {
            // Fallback: usar búsqueda directa
            try {
                const currentUser = await this.orm.call("res.users", "get_current_user", []);
                return currentUser.id;
            } catch (fallbackError) {
                console.error("No se pudo obtener el usuario actual:", fallbackError);
                return null;
            }
        }
    }

    /**
     * Cargar estadísticas de todos los tipos de caja
     */
    async loadStats() {
        try {
            console.log("Cargando estadísticas...");
            
            // Obtener el ID del usuario actual usando diferentes métodos
            let currentUserId = null;
            try {
                // Método 1: Usar session
                currentUserId = this.env.services?.user?.userId;
            } catch (e) {
                console.log("Método 1 falló:", e.message);
            }

            if (!currentUserId) {
                try {
                    // Método 2: Usar contexto
                    currentUserId = this.env.context?.uid;
                } catch (e) {
                    console.log("Método 2 falló:", e.message);
                }
            }

            if (!currentUserId) {
                // Método 3: Consultar directamente a la base de datos
                try {
                    const userInfo = await this.orm.call("res.users", "context_get", []);
                    currentUserId = userInfo.uid;
                } catch (e) {
                    console.log("Método 3 falló:", e.message);
                }
            }

            console.log("User ID obtenido:", currentUserId);

            if (!currentUserId) {
                console.error("No se pudo obtener el ID del usuario");
                // Si no podemos obtener el usuario, mostrar todas las cajas sin filtro
                await this.loadStatsWithoutUserFilter();
                return;
            }

            // Estadísticas de Caja Chica
            const pettyCashTotal = await this.orm.call(
                "petty.cash",
                "search_count",
                [[["responsible_id", "=", currentUserId]]]
            );
            
            const pettyCashOpen = await this.orm.call(
                "petty.cash", 
                "search_count",
                [[["responsible_id", "=", currentUserId], ["state", "=", "open"]]]
            );

            const pettyCashClosed = await this.orm.call(
                "petty.cash", 
                "search_count",
                [[["responsible_id", "=", currentUserId], ["state", "=", "closed"]]]
            );

            console.log("Petty Cash Stats:", {total: pettyCashTotal, open: pettyCashOpen, closed: pettyCashClosed});

            // Estadísticas de Caja de Distribución
            const distributionCashTotal = await this.orm.call(
                "distribution.cash",
                "search_count", 
                [[["responsible_id", "=", currentUserId]]]
            );

            const distributionCashOpen = await this.orm.call(
                "distribution.cash",
                "search_count",
                [[["responsible_id", "=", currentUserId], ["state", "=", "open"]]]
            );

            const distributionCashClosed = await this.orm.call(
                "distribution.cash",
                "search_count",
                [[["responsible_id", "=", currentUserId], ["state", "=", "closed"]]]
            );

            console.log("Distribution Cash Stats:", {total: distributionCashTotal, open: distributionCashOpen, closed: distributionCashClosed});

            // Estadísticas de Caja de Logística
            let logisticsCashTotal = 0, logisticsCashOpen = 0, logisticsCashClosed = 0;
            try {
                logisticsCashTotal = await this.orm.call(
                    "logistics.cash",
                    "search_count", 
                    [[["responsible_id", "=", currentUserId]]]
                );

                logisticsCashOpen = await this.orm.call(
                    "logistics.cash",
                    "search_count",
                    [[["responsible_id", "=", currentUserId], ["state", "=", "open"]]]
                );

                logisticsCashClosed = await this.orm.call(
                    "logistics.cash",
                    "search_count",
                    [[["responsible_id", "=", currentUserId], ["state", "=", "closed"]]]
                );
            } catch (logError) {
                console.log("Modelo logistics.cash no disponible aún:", logError.message);
            }

            console.log("Logistics Cash Stats:", {total: logisticsCashTotal, open: logisticsCashOpen, closed: logisticsCashClosed});

            // Actualizar el estado con todas las estadísticas
            this.state.stats = {
                petty_cash: { 
                    total: pettyCashTotal || 0, 
                    open: pettyCashOpen || 0, 
                    closed: pettyCashClosed || 0,
                    balance: 0 
                },
                distribution_cash: { 
                    total: distributionCashTotal || 0, 
                    open: distributionCashOpen || 0, 
                    closed: distributionCashClosed || 0,
                    balance: 0 
                },
                logistics_cash: { 
                    total: logisticsCashTotal || 0, 
                    open: logisticsCashOpen || 0, 
                    closed: logisticsCashClosed || 0,
                    balance: 0 
                }
            };

            console.log("Estadísticas finales cargadas:", this.state.stats);
            
        } catch (error) {
            console.error("Error loading stats:", error);
            // Establecer valores por defecto en caso de error
            this.state.stats = {
                petty_cash: { total: 0, open: 0, closed: 0, balance: 0 },
                distribution_cash: { total: 0, open: 0, closed: 0, balance: 0 },
                logistics_cash: { total: 0, open: 0, closed: 0, balance: 0 }
            };
        }
    }

    /**
     * Cargar estadísticas sin filtro de usuario (fallback)
     */
    async loadStatsWithoutUserFilter() {
        try {
            console.log("Cargando estadísticas sin filtro de usuario...");

            // Estadísticas totales sin filtro
            const pettyCashTotal = await this.orm.call("petty.cash", "search_count", [[]]);
            const pettyCashOpen = await this.orm.call("petty.cash", "search_count", [[["state", "=", "open"]]]);
            const pettyCashClosed = await this.orm.call("petty.cash", "search_count", [[["state", "=", "closed"]]]);

            const distributionCashTotal = await this.orm.call("distribution.cash", "search_count", [[]]);
            const distributionCashOpen = await this.orm.call("distribution.cash", "search_count", [[["state", "=", "open"]]]);
            const distributionCashClosed = await this.orm.call("distribution.cash", "search_count", [[["state", "=", "closed"]]]);

            let logisticsCashTotal = 0, logisticsCashOpen = 0, logisticsCashClosed = 0;
            try {
                logisticsCashTotal = await this.orm.call("logistics.cash", "search_count", [[]]);
                logisticsCashOpen = await this.orm.call("logistics.cash", "search_count", [[["state", "=", "open"]]]);
                logisticsCashClosed = await this.orm.call("logistics.cash", "search_count", [[["state", "=", "closed"]]]);
            } catch (logError) {
                console.log("Modelo logistics.cash no disponible:", logError.message);
            }

            this.state.stats = {
                petty_cash: { total: pettyCashTotal, open: pettyCashOpen, closed: pettyCashClosed, balance: 0 },
                distribution_cash: { total: distributionCashTotal, open: distributionCashOpen, closed: distributionCashClosed, balance: 0 },
                logistics_cash: { total: logisticsCashTotal, open: logisticsCashOpen, closed: logisticsCashClosed, balance: 0 }
            };

            console.log("Estadísticas cargadas (sin filtro):", this.state.stats);
            
        } catch (error) {
            console.error("Error en loadStatsWithoutUserFilter:", error);
        }
    }

    /**
     * Maneja la selección de tipo de caja
     */
    async onSelectCajaType(type) {
        this.state.selectedType = type;
        
        if (type === 'petty_cash') {
            // Abrir Caja Chica
            try {
                await this.actionService.doAction('petty_cash.action_petty_cash');
            } catch (error) {
                console.error("Error al abrir Caja Chica:", error);
                // Fallback: abrir directamente
                this.actionService.doAction({
                    name: _t("Caja Chica"),
                    type: 'ir.actions.act_window',
                    res_model: 'petty.cash',
                    view_mode: 'kanban,list,form',
                    target: 'current',
                    context: {
                        'default_state': 'draft',
                        'search_default_my_cajas': 1,
                    }
                });
            }
        } else if (type === 'distribution_cash') {
            // Abrir Caja de Distribución
            try {
                await this.actionService.doAction('petty_cash.action_distribution_cash');
            } catch (error) {
                console.error("Error al abrir Caja de Distribución:", error);
                // Fallback: abrir directamente
                this.actionService.doAction({
                    name: _t("Caja de Distribución"),
                    type: 'ir.actions.act_window',
                    res_model: 'distribution.cash',
                    view_mode: 'kanban,list,form',
                    target: 'current',
                    context: {
                        'default_state': 'draft',
                        'search_default_my_cajas': 1,
                    }
                });
            }
        } else if (type === 'logistics_cash') {
            // Abrir Caja de Logística
            try {
                await this.actionService.doAction('petty_cash.action_logistics_cash');
            } catch (error) {
                console.error("Error al abrir Caja de Logística:", error);
                // Fallback: abrir directamente
                this.actionService.doAction({
                    name: _t("Caja de Logística"),
                    type: 'ir.actions.act_window',
                    res_model: 'logistics.cash',
                    view_mode: 'kanban,list,form',
                    target: 'current',
                    context: {
                        'default_state': 'draft',
                        'search_default_my_cajas': 1,
                    }
                });
            }
        }
    }

    /**
     * Crear nueva caja chica directamente
     */
    async onCreateCajaChica() {
        try {
            await this.actionService.doAction('petty_cash.action_petty_cash_new');
        } catch (error) {
            console.error("Error al crear nueva caja chica:", error);
            // Fallback
            this.actionService.doAction({
                name: _t("Nueva Caja Chica"),
                type: 'ir.actions.act_window',
                res_model: 'petty.cash',
                view_mode: 'form',
                target: 'current',
                context: {
                    'default_state': 'draft',
                }
            });
        }
    }

    /**
     * Crear nueva caja de distribución directamente
     */
    async onCreateDistributionCash() {
        try {
            await this.actionService.doAction('petty_cash.action_distribution_cash_new');
        } catch (error) {
            console.error("Error al crear nueva caja de distribución:", error);
            // Fallback
            this.actionService.doAction({
                name: _t("Nueva Caja de Distribución"),
                type: 'ir.actions.act_window',
                res_model: 'distribution.cash',
                view_mode: 'form',
                target: 'current',
                context: {
                    'default_state': 'draft',
                }
            });
        }
    }

    /**
     * Crear nueva caja de logística directamente
     */
    async onCreateLogisticsCash() {
        try {
            await this.actionService.doAction('petty_cash.action_logistics_cash_new');
        } catch (error) {
            console.error("Error al crear nueva caja de logística:", error);
            // Fallback
            this.actionService.doAction({
                name: _t("Nueva Caja de Logística"),
                type: 'ir.actions.act_window',
                res_model: 'logistics.cash',
                view_mode: 'form',
                target: 'current',
                context: {
                    'default_state': 'draft',
                }
            });
        }
    }

    /**
     * Ver resumen de cajas chicas abiertas
     */
    async onViewOpenCajas() {
        try {
            const openCajas = await this.orm.call(
                "petty.cash",
                "search_count",
                [[["state", "=", "open"], ["responsible_id", "=", this.user.userId]]]
            );

            if (openCajas > 0) {
                await this.actionService.doAction('petty_cash.action_petty_cash_open');
            } else {
                this.notification.add(
                    _t("No hay cajas chicas abiertas actualmente."),
                    {
                        type: 'info',
                        title: _t("Sin Cajas Abiertas")
                    }
                );
            }
        } catch (error) {
            console.error("Error al consultar cajas chicas abiertas:", error);
            this.notification.add(
                _t("Error al consultar las cajas chicas abiertas."),
                {
                    type: 'danger',
                    title: _t("Error")
                }
            );
        }
    }

    /**
     * Ver resumen de cajas de distribución abiertas
     */
    async onViewOpenDistribution() {
        try {
            const openCajas = await this.orm.call(
                "distribution.cash",
                "search_count",
                [[["state", "=", "open"], ["responsible_id", "=", this.user.userId]]]
            );

            if (openCajas > 0) {
                await this.actionService.doAction('petty_cash.action_distribution_cash_open');
            } else {
                this.notification.add(
                    _t("No hay cajas de distribución abiertas actualmente."),
                    {
                        type: 'info',
                        title: _t("Sin Cajas de Distribución Abiertas")
                    }
                );
            }
        } catch (error) {
            console.error("Error al consultar cajas de distribución abiertas:", error);
            this.notification.add(
                _t("Error al consultar las cajas de distribución abiertas."),
                {
                    type: 'danger',
                    title: _t("Error")
                }
            );
        }
    }

    /**
     * Ver resumen de cajas de logística abiertas
     */
    async onViewOpenLogistics() {
        try {
            const openCajas = await this.orm.call(
                "logistics.cash",
                "search_count",
                [[["state", "=", "open"], ["responsible_id", "=", this.user.userId]]]
            );

            if (openCajas > 0) {
                await this.actionService.doAction('petty_cash.action_logistics_cash_open');
            } else {
                this.notification.add(
                    _t("No hay cajas de logística abiertas actualmente."),
                    {
                        type: 'info',
                        title: _t("Sin Cajas de Logística Abiertas")
                    }
                );
            }
        } catch (error) {
            console.error("Error al consultar cajas de logística abiertas:", error);
            this.notification.add(
                _t("Error al consultar las cajas de logística abiertas."),
                {
                    type: 'danger',
                    title: _t("Error")
                }
            );
        }
    }

    /**
     * Ver análisis simple
     */
    async onViewSimpleAnalysis() {
        try {
            this.actionService.doAction({
                name: _t("Movimientos de Logística"),
                type: 'ir.actions.act_window',
                res_model: 'logistics.cash.line',
                view_mode: 'list',
                context: {
                    'search_default_current_month': 1,
                }
            });
        } catch (error) {
            console.error("Error al abrir análisis:", error);
            this.notification.add(
                _t("Error al abrir el análisis."),
                {
                    type: 'danger',
                    title: _t("Error")
                }
            );
        }
    }

    /**
     * Recargar estadísticas
     */
    async onRefreshStats() {
        await this.loadStats();
        this.notification.add(
            _t("Estadísticas actualizadas correctamente."),
            {
                type: 'success',
                title: _t("Actualizado")
            }
        );
    }
}

// Registrar el componente para que esté disponible globalmente
registry.category("actions").add("caja_selection_widget", CajaSelectionWidget);
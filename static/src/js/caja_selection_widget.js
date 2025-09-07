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
                petty_cash: { total: 0, open: 0, balance: 0 },
                distribution_cash: { total: 0, open: 0, balance: 0 }
            }
        });

        onWillStart(async () => {
            await this.loadStats();
        });
    }

    /**
     * Cargar estadísticas de ambos tipos de caja
     */
    async loadStats() {
        try {
            // Estadísticas de Caja Chica
            const pettyCashStats = await this.orm.call(
                "petty.cash",
                "search_count",
                [[["responsible_id", "=", this.env.user.userId]]]
            );
            
            const pettyCashOpen = await this.orm.call(
                "petty.cash", 
                "search_count",
                [[["responsible_id", "=", this.env.user.userId], ["state", "=", "open"]]]
            );

            // Estadísticas de Caja de Distribución
            const distributionCashStats = await this.orm.call(
                "distribution.cash",
                "search_count", 
                [[["responsible_id", "=", this.env.user.userId]]]
            );

            const distributionCashOpen = await this.orm.call(
                "distribution.cash",
                "search_count",
                [[["responsible_id", "=", this.env.user.userId], ["state", "=", "open"]]]
            );

            this.state.stats = {
                petty_cash: { 
                    total: pettyCashStats, 
                    open: pettyCashOpen, 
                    balance: 0 
                },
                distribution_cash: { 
                    total: distributionCashStats, 
                    open: distributionCashOpen, 
                    balance: 0 
                }
            };
        } catch (error) {
            console.error("Error loading stats:", error);
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
            // Abrir Caja de Distribución (ya no está en construcción)
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
     * Ver resumen de cajas chicas abiertas
     */
    async onViewOpenCajas() {
        try {
            const openCajas = await this.orm.call(
                "petty.cash",
                "search_count",
                [[["state", "=", "open"]]]
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
                [[["state", "=", "open"]]]
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
     * Ver análisis simple
     */
    async onViewSimpleAnalysis() {
        try {
            this.actionService.doAction({
                name: _t("Movimientos de Distribución"),
                type: 'ir.actions.act_window',
                res_model: 'distribution.cash.line',
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
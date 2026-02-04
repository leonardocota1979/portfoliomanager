// static/js/app.js
/**
 * Portfolio Manager - Frontend JavaScript
 * 
 * Funções de interatividade, AJAX, e manipulação DOM
 * Versão: 2.0.0
 * Data: 26 de janeiro de 2026
 */

// ==============================================================================
// CONFIGURAÇÕES GLOBAIS
// ==============================================================================

const API_BASE_URL = window.location.origin;

// ==============================================================================
// UTILITÁRIOS
// ==============================================================================

/**
 * Faz requisição fetch com tratamento de erros
 * @param {string} url - URL da requisição
 * @param {object} options - Opções do fetch
 * @returns {Promise<object>} Resposta JSON
 */
async function apiFetch(url, options = {}) {
    try {
        const response = await fetch(url, {
            ...options,
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            }
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || 'Erro na requisição');
        }

        return data;
    } catch (error) {
        console.error('Erro na API:', error);
        throw error;
    }
}

/**
 * Mostra toast notification
 * @param {string} message - Mensagem a exibir
 * @param {string} type - Tipo: success, error, warning, info
 */
function showToast(message, type = 'info') {
    // Remove toast anterior se existir
    const existingToast = document.getElementById('toast');
    if (existingToast) {
        existingToast.remove();
    }

    // Cores por tipo
    const colors = {
        success: 'bg-green-500',
        error: 'bg-red-500',
        warning: 'bg-yellow-500',
        info: 'bg-blue-500'
    };

    // Cria toast
    const toast = document.createElement('div');
    toast.id = 'toast';
    toast.className = `fixed top-4 right-4 ${colors[type]} text-white px-6 py-3 rounded-lg shadow-lg z-50 transition-opacity duration-300`;
    toast.textContent = message;

    document.body.appendChild(toast);

    // Remove após 3 segundos
    setTimeout(() => {
        toast.style.opacity = '0';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

/**
 * Formata número como moeda
 * @param {number} value - Valor numérico
 * @param {string} currency - Código da moeda (padrão: USD)
 * @returns {string} Valor formatado
 */
function formatCurrency(value, currency = 'USD') {
    return new Intl.NumberFormat('pt-BR', {
        style: 'currency',
        currency: currency
    }).format(value);
}

/**
 * Formata percentual
 * @param {number} value - Valor numérico
 * @param {number} decimals - Casas decimais (padrão: 2)
 * @returns {string} Valor formatado
 */
function formatPercent(value, decimals = 2) {
    return `${value.toFixed(decimals)}%`;
}

/**
 * Confirma ação com o usuário
 * @param {string} message - Mensagem de confirmação
 * @returns {boolean} True se confirmado
 */
function confirmAction(message) {
    return confirm(message);
}

// ==============================================================================
// PORTFOLIO MANAGEMENT
// ==============================================================================

/**
 * Deleta um portfolio
 * @param {number} portfolioId - ID do portfolio
 */
async function deletePortfolio(portfolioId) {
    if (!confirmAction('Tem certeza que deseja deletar esta carteira? Esta ação não pode ser desfeita.')) {
        return;
    }

    try {
        await apiFetch(`${API_BASE_URL}/portfolios/${portfolioId}`, {
            method: 'DELETE'
        });

        showToast('Carteira deletada com sucesso!', 'success');
        
        // Recarrega página após 1 segundo
        setTimeout(() => {
            window.location.reload();
        }, 1000);
    } catch (error) {
        showToast(`Erro ao deletar carteira: ${error.message}`, 'error');
    }
}

/**
 * Atualiza nome/descrição do portfolio
 * @param {number} portfolioId - ID do portfolio
 * @param {object} data - Dados para atualizar
 */
async function updatePortfolio(portfolioId, data) {
    try {
        await apiFetch(`${API_BASE_URL}/portfolios/${portfolioId}`, {
            method: 'PUT',
            body: JSON.stringify(data)
        });

        showToast('Carteira atualizada com sucesso!', 'success');
        return true;
    } catch (error) {
        showToast(`Erro ao atualizar carteira: ${error.message}`, 'error');
        return false;
    }
}

// ==============================================================================
// ASSET CLASS MANAGEMENT
// ==============================================================================

/**
 * Cria nova asset class
 * @param {number} portfolioId - ID do portfolio
 * @param {object} data - Dados da asset class
 */
async function createAssetClass(portfolioId, data) {
    try {
        await apiFetch(`${API_BASE_URL}/asset-classes/?portfolio_id=${portfolioId}`, {
            method: 'POST',
            body: JSON.stringify(data)
        });

        showToast('Classe de ativo criada com sucesso!', 'success');
        return true;
    } catch (error) {
        showToast(`Erro ao criar classe: ${error.message}`, 'error');
        return false;
    }
}

/**
 * Deleta asset class
 * @param {number} assetClassId - ID da asset class
 */
async function deleteAssetClass(assetClassId) {
    if (!confirmAction('Deletar esta classe de ativo? Todos os ativos associados também serão removidos.')) {
        return;
    }

    try {
        await apiFetch(`${API_BASE_URL}/asset-classes/${assetClassId}`, {
            method: 'DELETE'
        });

        showToast('Classe deletada com sucesso!', 'success');
        setTimeout(() => window.location.reload(), 1000);
    } catch (error) {
        showToast(`Erro ao deletar: ${error.message}`, 'error');
    }
}

// ==============================================================================
// ASSET MANAGEMENT
// ==============================================================================

/**
 * Cria novo asset
 * @param {number} assetClassId - ID da asset class
 * @param {object} data - Dados do asset
 */
async function createAsset(assetClassId, data) {
    try {
        await apiFetch(`${API_BASE_URL}/assets/?asset_class_id=${assetClassId}`, {
            method: 'POST',
            body: JSON.stringify(data)
        });

        showToast('Ativo criado com sucesso!', 'success');
        return true;
    } catch (error) {
        showToast(`Erro ao criar ativo: ${error.message}`, 'error');
        return false;
    }
}

/**
 * Deleta asset
 * @param {number} assetId - ID do asset
 */
async function deleteAsset(assetId) {
    if (!confirmAction('Deletar este ativo?')) {
        return;
    }

    try {
        await apiFetch(`${API_BASE_URL}/assets/${assetId}`, {
            method: 'DELETE'
        });

        showToast('Ativo deletado com sucesso!', 'success');
        setTimeout(() => window.location.reload(), 1000);
    } catch (error) {
        showToast(`Erro ao deletar: ${error.message}`, 'error');
    }
}

// ==============================================================================
// PORTFOLIO ASSET MANAGEMENT
// ==============================================================================

/**
 * Adiciona asset ao portfolio
 * @param {number} portfolioId - ID do portfolio
 * @param {number} assetId - ID do asset
 * @param {object} data - Quantidade, targets, etc
 */
async function addAssetToPortfolio(portfolioId, assetId, data) {
    try {
        await apiFetch(`${API_BASE_URL}/portfolio-assets/?portfolio_id=${portfolioId}&asset_id=${assetId}`, {
            method: 'POST',
            body: JSON.stringify(data)
        });

        showToast('Ativo adicionado ao portfolio!', 'success');
        return true;
    } catch (error) {
        showToast(`Erro: ${error.message}`, 'error');
        return false;
    }
}

/**
 * Atualiza portfolio asset (quantidade, targets)
 * @param {number} portfolioAssetId - ID do portfolio asset
 * @param {object} data - Dados para atualizar
 */
async function updatePortfolioAsset(portfolioAssetId, data) {
    try {
        await apiFetch(`${API_BASE_URL}/portfolio-assets/${portfolioAssetId}`, {
            method: 'PUT',
            body: JSON.stringify(data)
        });

        showToast('Atualizado com sucesso!', 'success');
        return true;
    } catch (error) {
        showToast(`Erro: ${error.message}`, 'error');
        return false;
    }
}

/**
 * Remove asset do portfolio
 * @param {number} portfolioAssetId - ID do portfolio asset
 */
async function removeAssetFromPortfolio(portfolioAssetId) {
    if (!confirmAction('Remover este ativo do portfolio?')) {
        return;
    }

    try {
        await apiFetch(`${API_BASE_URL}/portfolio-assets/${portfolioAssetId}`, {
            method: 'DELETE'
        });

        showToast('Ativo removido!', 'success');
        setTimeout(() => window.location.reload(), 1000);
    } catch (error) {
        showToast(`Erro: ${error.message}`, 'error');
    }
}

// ==============================================================================
// DASHBOARD FUNCTIONS
// ==============================================================================

/**
 * Atualiza dados do dashboard
 * @param {number} portfolioId - ID do portfolio
 */
async function refreshDashboard(portfolioId) {
    try {
        showToast('Atualizando preços...', 'info');
        
        const data = await apiFetch(`${API_BASE_URL}/dashboard/api/${portfolioId}`);
        
        // Atualiza a página com novos dados
        window.location.reload();
    } catch (error) {
        showToast(`Erro ao atualizar: ${error.message}`, 'error');
    }
}

/**
 * Exporta dados do dashboard para CSV
 * @param {number} portfolioId - ID do portfolio
 */
async function exportDashboardCSV(portfolioId) {
    try {
        const data = await apiFetch(`${API_BASE_URL}/dashboard/api/${portfolioId}`);
        
        // Cria CSV
        let csv = 'Ativo,Ticker,Classe,Quantidade,Preço,Valor,% Atual,% Meta,Desvio,Status\n';
        
        data.assets_data.forEach(asset => {
            csv += `"${asset.name}","${asset.ticker}","${asset.asset_class_name}",`;
            csv += `${asset.quantity},${asset.current_price},${asset.current_value},`;
            csv += `${asset.current_percentage},${asset.target_percentage},${asset.deviation_percentage},`;
            csv += `"${asset.rebalance_status}"\n`;
        });
        
        // Download
        const blob = new Blob([csv], { type: 'text/csv' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `portfolio_${portfolioId}_${new Date().toISOString().split('T')[0]}.csv`;
        a.click();
        
        showToast('CSV exportado com sucesso!', 'success');
    } catch (error) {
        showToast(`Erro ao exportar: ${error.message}`, 'error');
    }
}

// ==============================================================================
// MODAL UTILITIES
// ==============================================================================

/**
 * Abre modal
 * @param {string} modalId - ID do modal
 */
function openModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.remove('hidden');
    }
}

/**
 * Fecha modal
 * @param {string} modalId - ID do modal
 */
function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.add('hidden');
    }
}

// ==============================================================================
// INICIALIZAÇÃO
// ==============================================================================

// Event listeners globais
document.addEventListener('DOMContentLoaded', () => {
    console.log('Portfolio Manager App Loaded 🚀');
    
    // Fecha modals ao clicar fora
    document.addEventListener('click', (e) => {
        if (e.target.classList.contains('modal-backdrop')) {
            e.target.classList.add('hidden');
        }
    });
    
    // Escape fecha modals
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            document.querySelectorAll('.modal-backdrop').forEach(modal => {
                modal.classList.add('hidden');
            });
        }
    });
});

// Expõe funções globalmente para uso inline em HTML
window.portfolioManager = {
    deletePortfolio,
    updatePortfolio,
    createAssetClass,
    deleteAssetClass,
    createAsset,
    deleteAsset,
    addAssetToPortfolio,
    updatePortfolioAsset,
    removeAssetFromPortfolio,
    refreshDashboard,
    exportDashboardCSV,
    openModal,
    closeModal,
    showToast,
    formatCurrency,
    formatPercent
};

// domain-approval.js
// Component for handling domain approval requests

class DomainApprovalManager {
    constructor() {
        this.pendingApprovals = {};
        this.nextRequestId = 1;
        this.setupUI();
    }
    
    setupUI() {
        // Create and append the approval dialog to the DOM
        const approvalDialog = document.createElement('div');
        approvalDialog.id = 'domain-approval-dialog';
        approvalDialog.classList.add('approval-dialog', 'hidden');
        
        approvalDialog.innerHTML = `
            <div class="approval-content">
                <div class="approval-header">
                    <h3>External Domain Access Request</h3>
                    <button class="close-button">&times;</button>
                </div>
                <div class="approval-body">
                    <p class="approval-message">Friday is requesting permission to access:</p>
                    <div class="domain-container">
                        <span class="domain-name"></span>
                    </div>
                    <p class="approval-reason"></p>
                    <div class="approval-warning">
                        <p>External websites may contain inaccurate or outdated information.</p>
                        <p>Only approve domains you trust.</p>
                    </div>
                </div>
                <div class="approval-footer">
                    <button class="deny-button">Deny</button>
                    <button class="approve-button">Approve</button>
                </div>
            </div>
        `;
        
        document.body.appendChild(approvalDialog);
        
        // Set up event listeners
        const closeButton = approvalDialog.querySelector('.close-button');
        const denyButton = approvalDialog.querySelector('.deny-button');
        const approveButton = approvalDialog.querySelector('.approve-button');
        
        closeButton.addEventListener('click', () => this.handleResponse(false));
        denyButton.addEventListener('click', () => this.handleResponse(false));
        approveButton.addEventListener('click', () => this.handleResponse(true));
    }
    
    handleResponse(approved) {
        const dialog = document.getElementById('domain-approval-dialog');
        dialog.classList.add('hidden');
        
        const currentRequestId = dialog.dataset.requestId;
        if (currentRequestId && this.pendingApprovals[currentRequestId]) {
            const { resolve } = this.pendingApprovals[currentRequestId];
            resolve({ approved });
            delete this.pendingApprovals[currentRequestId];
        }
    }
    
    requestApproval(domain, reason) {
        return new Promise((resolve) => {
            const requestId = this.nextRequestId++;
            this.pendingApprovals[requestId] = { domain, reason, resolve };
            
            const dialog = document.getElementById('domain-approval-dialog');
            dialog.dataset.requestId = requestId;
            
            // Update dialog content
            dialog.querySelector('.domain-name').textContent = domain;
            dialog.querySelector('.approval-reason').textContent = reason;
            
            // Show the dialog
            dialog.classList.remove('hidden');
        });
    }
}

// Export for use in main application
module.exports = DomainApprovalManager;
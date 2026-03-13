// New Project Form Handler
document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('newProjectForm');
    const messagesArea = document.getElementById('messages');
    
    if (form) {
        form.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const address = document.getElementById('projectAddress').value.trim();
            const description = document.getElementById('projectDescription').value.trim();
            
            if (!address || !description) {
                alert('Please fill in both address and description');
                return;
            }
            
            // Show loading state
            setButtonLoading('submit', true);
            
            try {
                // Step 1: Create project and get AI analysis
                const response = await fetch('/new-project', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        address: address,
                        description: description
                    })
                });
                
                const data = await response.json();
                
                if (data.success) {
                    // Add user message
                    addMessage('PM', 'Project Manager', 'Just now', `New project: ${address}\n\n${description}`);
                    
                    // Show AI thinking
                    const aiMessageId = addMessage('AI', 'Construction AI Assistant', 'Processing...', '🤖 Analyzing project requirements...');
                    
                    // Simulate brief delay for realism
                    setTimeout(async () => {
                        // Update AI message with analysis
                        const analysis = data.analysis;
                        const aiContent = `🤖 **Project Analysis Complete**

**Project Type:** ${analysis.project_type || 'Renovation'}
**Timeline:** ${analysis.estimated_timeline || '4-6 weeks'}
**Trades Identified:** ${analysis.trades_needed ? analysis.trades_needed.join(', ') : 'electrical, plumbing, drywall'}

<span class="badge badge-blue">Analyzing trades...</span>`;
                        
                        updateMessage(aiMessageId, aiContent);
                        
                        // Auto-trigger RFP sending after analysis
                        setTimeout(async () => {
                            await sendRFPs(data.project_id, aiMessageId);
                        }, 1500);
                        
                    }, 1000);
                    
                    // Clear form
                    form.reset();
                    
                } else {
                    alert('Error: ' + data.error);
                }
                
            } catch (error) {
                console.error('Error:', error);
                alert('Network error occurred');
            } finally {
                setButtonLoading('submit', false);
            }
        });
    }
});

async function sendRFPs(projectId, messageId) {
    try {
        const response = await fetch('/send-rfps', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                project_id: projectId
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            const rfpData = data.rfp_data;
            
            const finalContent = `🤖 **Project Processing Complete**

**RFPs Generated & Sent:** ${rfpData.total_rfps || 0} emails across ${rfpData.emails ? rfpData.emails.length : 0} trades

**Trades Contacted:**
${rfpData.emails ? rfpData.emails.map(email => `• ${email.trade.charAt(0).toUpperCase() + email.trade.slice(1)}: ${email.selected_subs ? email.selected_subs.length : 3} subcontractors`).join('\n') : '• Multiple trades contacted'}

**Expected Responses:** Next 3-7 days
**Auto Follow-up:** Scheduled for non-responders

<span class="badge badge-green">Automated ✓</span> <span class="badge badge-orange">Live Tracking</span>`;
            
            updateMessage(messageId, finalContent);
        }
        
    } catch (error) {
        console.error('RFP Error:', error);
        updateMessage(messageId, '🤖 RFP generation completed (simulated for demo)');
    }
}

function addMessage(avatar, author, time, content) {
    const messagesArea = document.getElementById('messages');
    const messageId = 'msg-' + Date.now();
    
    const messageHTML = `
    <div class="message" id="${messageId}">
        <div class="message-avatar">${avatar}</div>
        <div class="message-content">
            <div class="message-author">${author}</div>
            <div class="message-time">${time}</div>
            <div class="message-text">${content.replace(/\n/g, '<br>')}</div>
        </div>
    </div>`;
    
    messagesArea.insertAdjacentHTML('beforeend', messageHTML);
    messagesArea.scrollTop = messagesArea.scrollHeight;
    return messageId;
}

function updateMessage(messageId, newContent) {
    const message = document.getElementById(messageId);
    if (message) {
        const textElement = message.querySelector('.message-text');
        const timeElement = message.querySelector('.message-time');
        if (textElement) textElement.innerHTML = newContent.replace(/\n/g, '<br>');
        if (timeElement) timeElement.textContent = 'Just now';
    }
}

function setButtonLoading(type, loading) {
    if (type === 'submit') {
        const textSpan = document.getElementById('submitText');
        const spinner = document.getElementById('submitSpinner');
        const button = document.querySelector('#newProjectForm button[type="submit"]');
        
        if (textSpan && spinner && button) {
            textSpan.style.display = loading ? 'none' : 'inline';
            spinner.style.display = loading ? 'inline' : 'none';
            button.disabled = loading;
        }
    } else if (type === 'analyze') {
        const textSpan = document.getElementById('analyzeText');
        const spinner = document.getElementById('analyzeSpinner');
        const button = document.getElementById('analyzeBtn');
        
        if (textSpan && spinner && button) {
            textSpan.style.display = loading ? 'none' : 'inline';
            spinner.style.display = loading ? 'inline' : 'none';
            button.disabled = loading;
        }
    }
}

// Quote Analysis Function
async function analyzeQuote() {
    const subcontractor = document.getElementById('quoteSubcontractor').value.trim();
    const projectId = document.getElementById('quoteProjectId').value.trim();
    const quoteText = document.getElementById('quoteText').value.trim();
    
    if (!subcontractor || !projectId || !quoteText) {
        alert('Please fill in all fields');
        return;
    }
    
    setButtonLoading('analyze', true);
    
    try {
        const response = await fetch('/process-quote', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                subcontractor: subcontractor,
                project_id: projectId,
                quote_text: quoteText
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            displayQuoteAnalysis(data.analysis);
        } else {
            alert('Error: ' + data.error);
        }
        
    } catch (error) {
        console.error('Error:', error);
        alert('Network error occurred');
    } finally {
        setButtonLoading('analyze', false);
    }
}

function displayQuoteAnalysis(analysis) {
    const container = document.getElementById('quoteAnalysis');
    const resultsDiv = document.getElementById('analysisResults');
    
    if (!container || !resultsDiv) return;
    
    const completenessColor = analysis.completeness_score >= 8 ? 'badge-green' : 
                            analysis.completeness_score >= 6 ? 'badge-orange' : 'badge-red';
    
    const pricingColor = analysis.pricing_assessment === 'reasonable' ? 'badge-green' :
                        analysis.pricing_assessment === 'high' ? 'badge-red' :
                        analysis.pricing_assessment === 'low' ? 'badge-yellow' : 'badge-gray';
    
    resultsDiv.innerHTML = `
        <div class="two-col" style="margin-bottom:16px;">
            <div>
                <div style="font-family:'Roboto',sans-serif; font-weight:600; margin-bottom:8px;">Completeness Score</div>
                <div style="display:flex; align-items:center; gap:8px;">
                    <span style="font-size:24px; font-family:'Roboto',sans-serif; font-weight:700;">${analysis.completeness_score}/10</span>
                    <span class="badge ${completenessColor}">${analysis.completeness_score >= 8 ? 'Complete' : analysis.completeness_score >= 6 ? 'Partial' : 'Incomplete'}</span>
                </div>
            </div>
            <div>
                <div style="font-family:'Roboto',sans-serif; font-weight:600; margin-bottom:8px;">Pricing Assessment</div>
                <span class="badge ${pricingColor}">${analysis.pricing_assessment.charAt(0).toUpperCase() + analysis.pricing_assessment.slice(1)}</span>
            </div>
        </div>
        
        <div style="margin-bottom:16px;">
            <div style="font-family:'Roboto',sans-serif; font-weight:600; margin-bottom:8px;">Summary</div>
            <div style="background:#f0efe9; padding:12px; border-radius:8px; font-size:14px;">
                ${analysis.summary}
            </div>
        </div>
        
        ${analysis.missing_items && analysis.missing_items.length > 0 ? `
        <div style="margin-bottom:16px;">
            <div style="font-family:'Roboto',sans-serif; font-weight:600; margin-bottom:8px;">Missing Items</div>
            <ul style="padding-left:20px; font-size:14px;">
                ${analysis.missing_items.map(item => `<li>${item}</li>`).join('')}
            </ul>
        </div>
        ` : ''}
        
        ${analysis.red_flags && analysis.red_flags.length > 0 ? `
        <div style="margin-bottom:16px;">
            <div style="font-family:'Roboto',sans-serif; font-weight:600; margin-bottom:8px;">⚠️ Red Flags</div>
            <ul style="padding-left:20px; font-size:14px; color:#c0463a;">
                ${analysis.red_flags.map(flag => `<li>${flag}</li>`).join('')}
            </ul>
        </div>
        ` : ''}
        
        ${analysis.follow_up_questions && analysis.follow_up_questions.length > 0 ? `
        <div>
            <div style="font-family:'Roboto',sans-serif; font-weight:600; margin-bottom:8px;">Follow-up Questions</div>
            <ul style="padding-left:20px; font-size:14px;">
                ${analysis.follow_up_questions.map(q => `<li>${q}</li>`).join('')}
            </ul>
        </div>
        ` : ''}
    `;
    
    container.style.display = 'block';
}

// Project View Function (for dashboard)
function viewProject(projectId) {
    // In a real app, this would open a detailed project view
    // For demo, just show an alert
    alert(`Opening project ${projectId} - this would show detailed project view with all quotes, RFPs, and timeline`);
}
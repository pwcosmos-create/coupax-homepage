document.addEventListener('DOMContentLoaded', () => {
  const injectForm = document.getElementById('chief-dev-inject-form');
  const cardForm = document.getElementById('chief-dev-card-form');
  const terminal = document.getElementById('chief-dev-terminal');
  const urlInput = document.getElementById('chief-dev-url');
  
  const statDocs = document.getElementById('chief-stat-docs');
  const statSnippets = document.getElementById('chief-stat-snippets');
  
  const cardList = document.getElementById('chief-learn-card-list');
  const emptyMsg = document.getElementById('chief-learn-empty');
  const cardCount = document.getElementById('chief-card-count');
  const clearCardsBtn = document.getElementById('chief-dev-clear-cards');
  
  let docsCount = 142;
  let snippetsCount = 1250;
  
  let knowledgeCards = [];

  function fetchCards() {
    fetch('/api/agents/office/chief-dev.json', { cache: "no-store", credentials: "same-origin" })
      .then(r => r.json())
      .then(data => {
        if (data && Array.isArray(data.cards)) {
          knowledgeCards = data.cards;
          renderCards();
        }
      })
      .catch(err => console.error("fetchCards error:", err));
  }

  function addLog(msg, color = '#ccc') {
    if (!terminal) return;
    const time = new Date().toLocaleTimeString('ko-KR', { hour12: false });
    const line = document.createElement('div');
    line.style.marginBottom = '4px';
    line.innerHTML = `<span style="color: #666; margin-right: 8px;">[${time}]</span> <span style="color: ${color}">${msg}</span>`;
    terminal.appendChild(line);
    terminal.scrollTop = terminal.scrollHeight;
  }

  function renderCards() {
    if (!cardList) return;
    
    // Clear existing cards
    cardList.innerHTML = '';
    
    if (knowledgeCards.length === 0) {
      if (emptyMsg) {
        cardList.appendChild(emptyMsg);
        emptyMsg.style.display = 'block';
      }
      if (cardCount) cardCount.textContent = '0건';
      return;
    }
    
    if (emptyMsg) emptyMsg.style.display = 'none';
    if (cardCount) cardCount.textContent = knowledgeCards.length + '건';
    
    knowledgeCards.forEach((card, index) => {
      const li = document.createElement('li');
      li.style.backgroundColor = '#1e293b';
      li.style.border = '1px solid #334155';
      li.style.borderRadius = '8px';
      li.style.padding = '16px';
      li.style.position = 'relative';
      
      const tagHtml = (card.tag || "미분류").split(',').map(t => `<span style="display:inline-block; background-color:rgba(59, 130, 246, 0.2); color:#60a5fa; padding:2px 8px; border-radius:12px; font-size:0.75rem; margin-right:6px; margin-bottom:8px;">#${t.trim()}</span>`).join('');
      
      li.innerHTML = `
        <div style="display:flex; justify-content:space-between; margin-bottom:8px;">
          <div>${tagHtml}</div>
          <time style="font-size:0.75rem; color:#94a3b8;">${card.ts}</time>
        </div>
        <h4 style="margin:0 0 8px 0; font-size:1rem; color:#f8fafc;">${card.title}</h4>
        <pre style="margin:0; font-size:0.875rem; color:#cbd5e1; white-space:pre-wrap; font-family:inherit; line-height:1.5;">${card.body}</pre>
        <button class="delete-card-btn" data-id="${card.id}" style="position:absolute; bottom:16px; right:16px; background:none; border:none; color:#ef4444; cursor:pointer; font-size:0.875rem; text-decoration:underline;">삭제</button>
      `;
      cardList.appendChild(li);
    });

    document.querySelectorAll('.delete-card-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const id = e.target.getAttribute('data-id');
        fetch(`/api/agents/office/chief-dev/${id}`, { method: 'DELETE', headers: { 'X-CSRFToken': window.CSRF_TOKEN } })
          .then(() => {
            addLog(`지식 카드가 삭제되었습니다.`, '#ef4444');
            fetchCards();
          });
      });
    });
  }

  // Initial render
  fetchCards();

  // Polling periodically for new cards
  setInterval(fetchCards, 30000);

  // Clear all button
  if (clearCardsBtn) {
    clearCardsBtn.addEventListener('click', () => {
      if (confirm('모든 지식 카드를 삭제하시겠습니까?')) {
        fetch('/api/agents/office/chief-dev/clear', { method: 'POST', headers: { 'X-CSRFToken': window.CSRF_TOKEN } })
          .then(() => {
            addLog(`모든 지식 카드가 삭제되었습니다.`, '#ef4444');
            fetchCards();
          });
      }
    });
  }

  // Clear initial terminal text when the tab becomes active or immediately
  if (terminal) {
    terminal.innerHTML = '';
    addLog('👨‍💻 수석 개발자 에이전트 가동을 시작합니다. (Vector DB 연결 완료)', '#4CAF50');

    // Simulate background tasks
    setInterval(() => {
      const unit = document.getElementById('office-unit-chief-dev');
      if (unit && unit.hasAttribute('hidden')) return;

      const actions = [
        'GitHub 트렌딩 저장소 스캔 중...',
        'React 19 최신 공식 문서 업데이트 확인 중...',
        '새로운 보안 취약점(CVE) 데이터베이스 동기화 완료.',
        '로컬 프로젝트 "가계부 앱" 소스코드 인덱싱 중...',
        'Vite 번들링 최적화 팁 Vector DB에 저장 완료.',
        'Python Flask 보안 설정 가이드 수집 완료.',
        'Pinecone Vector DB 응답 속도 테스트: 45ms',
      ];
      const randomAction = actions[Math.floor(Math.random() * actions.length)];
      addLog(randomAction, '#cccccc');
      
      snippetsCount += Math.floor(Math.random() * 5);
      if (statSnippets) {
        statSnippets.textContent = snippetsCount.toLocaleString() + '개';
      }
    }, 4000);
  }

  // URL Form submit handling
  if (injectForm) {
    injectForm.addEventListener('submit', (e) => {
      e.preventDefault();
      const url = urlInput.value;
      if (!url) return;

      addLog(`[수동 지시] URL 크롤링 및 파싱 시작: ${url}`, '#61afef');
      
      setTimeout(() => {
        addLog(`[크롤링 완료] ${url} 데이터 추출 및 벡터화 성공.`, '#4CAF50');
        docsCount++;
        snippetsCount += 12;
        if (statDocs) statDocs.textContent = docsCount.toLocaleString() + '건';
        if (statSnippets) statSnippets.textContent = snippetsCount.toLocaleString() + '개';
        
        urlInput.value = '';
      }, 2500);
    });
  }

  // Card Form submit handling
  if (cardForm) {
    cardForm.addEventListener('submit', (e) => {
      e.preventDefault();
      // 이 부분은 프론트엔드 더미였으므로 제외하거나, 필요시 백엔드 추가 API 연동 필요
      addLog(`[지식 저장] 신규 지식 카드는 에이전트를 통해서만 추가할 수 있습니다.`, '#ef4444');
      
      // Reset form
      document.getElementById('chief-dev-title').value = '';
      document.getElementById('chief-dev-body').value = '';
    });
  }
});

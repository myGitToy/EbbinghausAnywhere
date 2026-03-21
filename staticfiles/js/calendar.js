/**
 * 复习日历页面 - 使用 FullCalendar 展示复习计划
 */
(function() {
  'use strict';

  // 工具函数：获取CSRF Token
  function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
      const cookies = document.cookie.split(';');
      for (let i = 0; i < cookies.length; i++) {
        const cookie = cookies[i].trim();
        if (cookie.substring(0, name.length + 1) === (name + '=')) {
          cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
          break;
        }
      }
    }
    return cookieValue;
  }

  // 全局日历实例
  let calendarInstance = null;

  // 初始化日历
  function initCalendar() {
    const calendarEl = document.getElementById('calendar');
    const loadingEl = document.getElementById('calendar-loading');
    
    if (!calendarEl) {
      console.error('Calendar element not found');
      return;
    }

    try {
      calendarInstance = new FullCalendar.Calendar(calendarEl, {
        initialView: 'dayGridMonth',
        locale: 'zh-cn',
        headerToolbar: {
          left: 'prev,next today',
          center: 'title',
          right: 'dayGridMonth,dayGridWeek'
        },
        buttonText: {
          today: '今天',
          month: '月',
          week: '周'
        },
        events: function(info, successCallback, failureCallback) {
          const url = `/api/calendar-events/?start=${info.startStr}&end=${info.endStr}`;
          fetch(url, { 
            credentials: 'same-origin',
            headers: {
              'Accept': 'application/json'
            }
          })
            .then(response => {
              if (!response.ok) throw new Error('Network response was not ok');
              return response.json();
            })
            .then(data => {
              successCallback(data);
            })
            .catch(err => {
              console.error('Failed to load calendar events:', err);
              failureCallback(err);
            });
        },
        eventContent: function(arg) {
          const event = arg.event;
          const pending = event.extendedProps.pending || 0;
          const completed = event.extendedProps.completed || 0;
          const overdue = event.extendedProps.overdue || 0;
          
          let html = '<div class="fc-event-main-frame">';
          html += '<div class="fc-event-title-container">';
          html += `<div class="fc-event-title">${arg.event.title}</div>`;
          if (overdue > 0) {
            html += `<div class="fc-event-overdue text-danger">逾期: ${overdue}</div>`;
          }
          html += '</div></div>';
          
          return { html: html };
        },
        dateClick: function(info) {
          openDayModal(info.dateStr);
        },
        eventClick: function(info) {
          info.jsEvent.preventDefault();
          const dateStr = info.event.startStr;
          openDayModal(dateStr);
        },
        loading: function(isLoading) {
          // 可以在这里添加加载指示器
        }
      });

      calendarInstance.render();
      
      // 隐藏加载提示，显示日历
      if (loadingEl) loadingEl.style.display = 'none';
      calendarEl.style.display = 'block';
      
    } catch (e) {
      console.error('Failed to initialize FullCalendar', e);
      if (loadingEl) {
        loadingEl.innerHTML = '<div class="alert alert-danger">日历初始化失败: ' + e.message + '</div>';
      }
    }
  }

  // 等待 FullCalendar 加载
  function waitForFullCalendar() {
    if (typeof window.FullCalendar !== 'undefined') {
      initCalendar();
    } else {
      let waited = 0;
      const interval = setInterval(() => {
        if (typeof window.FullCalendar !== 'undefined') {
          clearInterval(interval);
          initCalendar();
        }
        waited += 100;
        if (waited > 10000) { // 增加到10秒
          clearInterval(interval);
          const loadingEl = document.getElementById('calendar-loading');
          if (loadingEl) {
            loadingEl.innerHTML = '<div class="alert alert-danger">日历组件加载超时，请刷新页面重试</div>';
          }
          console.error('FullCalendar did not load within 10s');
        }
      }, 100);
    }
  }

  // 打开日期详情弹窗
  function openDayModal(dateStr) {
    const modalBody = document.getElementById('calendarDayModalBody');
    const modalTitle = document.getElementById('calendarDayModalLabel');
    const modalElement = document.getElementById('calendarDayModal');
    
    if (!modalBody || !modalTitle || !modalElement) {
      console.error('Modal body not found');
      return;
    }

    modalTitle.textContent = dateStr + ' 的复习';
    
    // 显示加载状态
    modalBody.innerHTML = `
      <div class="text-center py-3">
        <div class="spinner-border text-primary" role="status">
          <span class="visually-hidden">加载中...</span>
        </div>
      </div>
    `;

    // 显示模态框
    bootstrap.Modal.getOrCreateInstance(modalElement).show();

    // 获取当天复习项目
    fetch(`/api/calendar-day-items/?date=${dateStr}`, { 
      credentials: 'same-origin',
      headers: {
        'Accept': 'application/json'
      }
    })
      .then(resp => {
        if (!resp.ok) throw new Error('Network response was not ok');
        return resp.json();
      })
      .then(data => {
        if (data.error) {
          modalBody.innerHTML = `<div class="alert alert-danger">${data.error}</div>`;
        } else if (data.items && data.items.length > 0) {
          renderDayItems(data.items, dateStr, modalBody);
        } else {
          modalBody.innerHTML = '<div class="alert alert-info">当天没有需要复习的单词。</div>';
        }
      })
      .catch(err => {
        console.error('Failed to load day items:', err);
        modalBody.innerHTML = '<div class="alert alert-danger">加载失败，请重试</div>';
      });
  }

  // 渲染日期项目列表
  function renderDayItems(items, dateStr, container) {
    const list = document.createElement('div');
    list.className = 'list-group';

    items.forEach(it => {
      const itemDiv = document.createElement('div');
      itemDiv.className = 'list-group-item';
      itemDiv.dataset.itemId = it.id;
      
      // 构建HTML
      let itemHtml = `
        <div class="d-flex justify-content-between align-items-start">
          <div class="flex-grow-1">
            <h5 class="mb-1">${escapeHtml(it.item)}</h5>
            <p class="mb-1 text-muted">
              <small>周期: ${it.interval_day} 天</small>
              ${it.unfamiliar_count > 0 ? `<span class="badge bg-warning text-dark ms-2">不熟: ${it.unfamiliar_count}</span>` : ''}
            </p>
            <small class="text-muted">下次复习: ${it.next_review_date || '-'}</small>
          </div>
          <div class="btn-group-vertical btn-group-sm ms-3" role="group">
            <a href="${it.detail_url}" class="btn btn-outline-primary" target="_blank">详情</a>
            <button class="btn btn-success btn-feedback" data-action="yes" data-id="${it.id}">
              已掌握
            </button>
            <button class="btn btn-warning btn-feedback" data-action="no" data-id="${it.id}">
              不熟
            </button>
            <button class="btn btn-secondary btn-feedback" data-action="reset" data-id="${it.id}">
              重置
            </button>
          </div>
        </div>
      `;

      itemDiv.innerHTML = itemHtml;
      
      // 绑定反馈按钮事件
      itemDiv.querySelectorAll('.btn-feedback').forEach(btn => {
        btn.addEventListener('click', function(e) {
          e.preventDefault();
          const action = this.dataset.action;
          const itemId = this.dataset.id;
          handleFeedback(action, itemId, dateStr, itemDiv);
        });
      });

      list.appendChild(itemDiv);
    });

    container.innerHTML = '';
    container.appendChild(list);
  }

  // 处理反馈操作
  function handleFeedback(action, itemId, dateStr, itemDiv) {
    if (action === 'reset' && !confirm('确认重置该单词的复习周期？')) {
      return;
    }

    const urlMap = {
      'yes': '/review-feedback/yes/',
      'no': '/review-feedback/no/',
      'reset': '/review-feedback/reset/'
    };

    const url = urlMap[action];
    if (!url) {
      console.error('Unknown action:', action);
      return;
    }

    const buttons = itemDiv.querySelectorAll('.btn-feedback');
    buttons.forEach(b => b.disabled = true);

    const csrftoken = getCookie('csrftoken');
    const payload = { id: parseInt(itemId), date: dateStr };

    fetch(url, {
      method: 'POST',
      credentials: 'same-origin',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrftoken,
        'Accept': 'application/json'
      },
      body: JSON.stringify(payload)
    })
      .then(r => {
        if (!r.ok) throw new Error('Network response was not ok');
        return r.json();
      })
      .then(resp => {
        if (resp && resp.success) {
          // 更新UI显示已点评
          const btnGroup = itemDiv.querySelector('.btn-group-vertical');
          if (btnGroup) {
            btnGroup.innerHTML = '<span class="badge bg-success">已点评</span>';
          }
          
          // 刷新日历事件
          if (calendarInstance) {
            calendarInstance.refetchEvents();
          }
        } else {
          alert((resp && resp.message) || '操作失败');
          buttons.forEach(b => b.disabled = false);
        }
      })
      .catch(err => {
        console.error('Feedback error:', err);
        alert('网络错误，操作失败');
        buttons.forEach(b => b.disabled = false);
      });
  }

  // HTML转义函数
  function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  // 监听模态框关闭事件，刷新日历
  document.addEventListener('DOMContentLoaded', function() {
    const modal = document.getElementById('calendarDayModal');
    if (modal) {
      modal.addEventListener('hidden.bs.modal', function () {
        if (calendarInstance) {
          calendarInstance.refetchEvents();
        }
      });
    }
  });

  // 页面加载完成后初始化
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', waitForFullCalendar);
  } else {
    waitForFullCalendar();
  }

})();

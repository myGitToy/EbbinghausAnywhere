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
  
  // 悬浮窗元素
  let tooltipEl = null;
  let tooltipTimeout = null;

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
          console.log('Fetching events for:', info.startStr, 'to', info.endStr);
          
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
              console.log('Loaded', data.length, 'events');
              successCallback(data);
            })
            .catch(err => {
              console.error('Failed to load calendar events:', err);
              failureCallback(err);
            });
        },
        eventContent: function(arg) {
          const event = arg.event;
          const props = event.extendedProps;
          const todayPending = props.today_pending || 0;
          const todayCompleted = props.today_completed || 0;
          const extra = props.extra || 0;
          
          let html = '<div class="fc-event-main-frame">';
          html += '<div class="fc-event-title-container">';
          html += `<div class="fc-event-title fc-sticky">${arg.event.title}</div>`;
          
          // 显示详细分类信息（不包括逾期）
          let details = [];
          if (todayPending > 0) details.push(`今日待: ${todayPending}`);
          if (todayCompleted > 0) details.push(`已完成: ${todayCompleted}`);
          if (extra > 0) details.push(`额外: ${extra}`);
          
          if (details.length > 0) {
            html += `<div class="fc-event-subtitle">${details.join(' | ')}</div>`;
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
        eventMouseEnter: function(info) {
          // 延迟显示悬浮窗
          clearTimeout(tooltipTimeout);
          tooltipTimeout = setTimeout(() => {
            showTooltip(info);
          }, 300);
        },
        eventMouseLeave: function(info) {
          // 取消悬浮窗显示
          clearTimeout(tooltipTimeout);
          if (isLoading) {
            console.log('Calendar loading...');
          } else {
            console.log('Calendar loading complete');
          }
        },
        datesSet: function(dateInfo) {
          // 当月份改变时调用
          console.log('Date range changed:', dateInfo.startStr, 'to', dateInfo.endStr);
        },
        loading: function(isLoading) {
          // 可以在这里添加加载指示器
        }
      });

      calendarInstance.render();
      
      // 强制显示日历
      setTimeout(() => {
        if (loadingEl) {
          loadingEl.style.display = 'none';
          loadingEl.style.visibility = 'hidden';
        }
        calendarEl.style.display = 'block';
        calendarEl.style.visibility = 'visible';
        calendarEl.style.opacity = '1';
        
        // 强制更新大小
        if (calendarInstance) {
          calendarInstance.updateSize();
          console.log('Calendar rendered and sized');
        }
      }, 50);
      
      // 再次确保渲染
      setTimeout(() => {
        if (calendarInstance) {
          calendarInstance.updateSize();
          console.log('Calendar size re-updated');
        }
      }, 300);
      
    } catch (e) {
      console.error('Failed to initialize FullCalendar', e);
      if (loadingEl) {
        loadingEl.innerHTML = '<div class="alert alert-danger">日历初始化失败: ' + e.message + '</div>';
      }
    }
  }

  // 显示悬浮窗
  function showTooltip(info) {
    const dateStr = info.event.startStr;
    
    // 创建或获取悬浮窗元素
    if (!tooltipEl) {
      tooltipEl = document.createElement('div');
      tooltipEl.className = 'calendar-tooltip';
      document.body.appendChild(tooltipEl);
    }
    
    // 显示加载状态
    tooltipEl.innerHTML = '<div class="tooltip-loading">加载中...</div>';
    tooltipEl.style.display = 'block';
    
    // 定位悬浮窗
    positionTooltip(info.jsEvent, tooltipEl);
    
    // 获取单词列表
    fetch(`/api/calendar-day-items/?date=${dateStr}`, { 
      credentials: 'same-origin',
      headers: {
        'Accept': 'application/json'
      }
    })
      .then(resp => resp.json())
      .then(data => {
        if (data.error) {
          tooltipEl.innerHTML = `<div class="tooltip-error">${data.error}</div>`;
        } else if (data.items && data.items.length > 0) {
          renderTooltipContent(data.items, dateStr);
        } else {
          tooltipEl.innerHTML = '<div class="tooltip-empty">当天无复习项</div>';
        }
        // 重新定位以适应内容
        positionTooltip(info.jsEvent, tooltipEl);
      })
      .catch(err => {
        console.error('Failed to load tooltip data:', err);
        tooltipEl.innerHTML = '<div class="tooltip-error">加载失败</div>';
      });
  }

  // 隐藏悬浮窗
  function hideTooltip() {
    if (tooltipEl) {
      tooltipEl.style.display = 'none';
    }
  }

  // 定位悬浮窗
  function positionTooltip(jsEvent, tooltip) {
    const x = jsEvent.pageX;
    const y = jsEvent.pageY;
    const offset = 10;
    
    // 获取窗口尺寸
    const winWidth = window.innerWidth;
    const winHeight = window.innerHeight;
    const scrollX = window.pageXOffset;
    const scrollY = window.pageYOffset;
    
    // 获取悬浮窗尺寸
    const tooltipRect = tooltip.getBoundingClientRect();
    const tooltipWidth = tooltipRect.width || 300;
    const tooltipHeight = tooltipRect.height || 200;
    
    // 默认位置：鼠标右下方
    let left = x + offset;
    let top = y + offset;
    
    // 如果右侧空间不足，显示在左侧
    if (left + tooltipWidth > scrollX + winWidth) {
      left = x - tooltipWidth - offset;
    }
    
    // 如果下方空间不足，显示在上方
    if (top + tooltipHeight > scrollY + winHeight) {
      top = y - tooltipHeight - offset;
    }
    
    // 确保不超出左边界和上边界
    left = Math.max(scrollX + 5, left);
    top = Math.max(scrollY + 5, top);
    
    tooltip.style.left = left + 'px';
    tooltip.style.top = top + 'px';
  }

  // 渲染悬浮窗内容
  function renderTooltipContent(items, dateStr) {
    if (!tooltipEl) return;
    
    // 按类别分组
    const todayPlanned = [];
    const extra = [];
    
    const today = new Date(dateStr);
    today.setHours(0, 0, 0, 0);
    
    items.forEach(it => {
      if (it.is_extra_review) {
        extra.push(it);
      } else if (it.next_review_date) {
        const reviewDate = new Date(it.next_review_date);
        reviewDate.setHours(0, 0, 0, 0);
        
        if (reviewDate.getTime() === today.getTime()) {
          todayPlanned.push(it);
        }
      }
    });
    
    let html = `<div class="tooltip-header">${dateStr} 的复习</div>`;
    html += '<div class="tooltip-body">';
    
    // 今日计划
    if (todayPlanned.length > 0) {
      html += '<div class="tooltip-section">';
      html += `<div class="tooltip-section-title">今日计划 (${todayPlanned.length})</div>`;
      html += '<ul class="tooltip-list">';
      todayPlanned.slice(0, 10).forEach(it => {
        const status = it.reviewed_today ? '<span class="tooltip-badge done">✓</span>' : '';
        html += `<li>${escapeHtml(it.item)} ${status}</li>`;
      });
      if (todayPlanned.length > 10) {
        html += `<li class="tooltip-more">...还有 ${todayPlanned.length - 10} 个</li>`;
      }
      html += '</ul></div>';
    }
    
    // 额外复习
    if (extra.length > 0) {
      html += '<div class="tooltip-section">';
      html += `<div class="tooltip-section-title">额外复习 (${extra.length})</div>`;
      html += '<ul class="tooltip-list">';
      extra.slice(0, 5).forEach(it => {
        html += `<li>${escapeHtml(it.item)}</li>`;
      });
      if (extra.length > 5) {
        html += `<li class="tooltip-more">...还有 ${extra.length - 5} 个</li>`;
      }
      html += '</ul></div>';
    }
    
    html += '</div>';
    html += '<div class="tooltip-footer">点击查看详情</div>';
    
    tooltipEl.innerHTML = html;
  }

  // 等待 FullCalendar 加载
  function waitForFullCalendar() {
    const loadingEl = document.getElementById('calendar-loading');
    
    if (typeof window.FullCalendar !== 'undefined') {
      console.log('FullCalendar loaded successfully');
      initCalendar();
    } else {
      let waited = 0;
      const interval = setInterval(() => {
        if (typeof window.FullCalendar !== 'undefined') {
          clearInterval(interval);
          console.log('FullCalendar loaded after', waited, 'ms');
          initCalendar();
        }
        waited += 100;
        if (waited > 10000) { // 增加到10秒
          clearInterval(interval);
          console.error('FullCalendar did not load within 10s');
          if (loadingEl) {
            loadingEl.innerHTML = `
              <div class="alert alert-danger">
                <h5>日历组件加载超时</h5>
                <p>请尝试以下操作：</p>
                <ul>
                  <li>刷新页面重试</li>
                  <li>检查浏览器控制台是否有错误</li>
                  <li>清除浏览器缓存后重试</li>
                </ul>
                <button class="btn btn-primary" onclick="location.reload()">刷新页面</button>
              </div>
            `;
          }
        }
      }, 100);
    }
  }

  // 打开日期详情弹窗
  function openDayModal(dateStr) {
    const modalBody = document.getElementById('calendarDayModalBody');
    const modalTitle = document.getElementById('calendarDayModalLabel');
    
    if (!modalBody) {
      console.error('Modal body not found');
      return;
    }

    modalTitle.textContent = dateStr + ' 的复习';
    
    // 显示加载状态
    modalBody.innerHTML = `
      <div class="text-center py-3">
        <div class="spinner-border text-primary" role="status">
          <span class="sr-only">加载中...</span>
        </div>
      </div>
    `;

    // 显示模态框
    if (typeof $ !== 'undefined' && $.fn.modal) {
      $('#calendarDayModal').modal('show');
    }

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
    if (!items || items.length === 0) {
      container.innerHTML = '<div class="alert alert-info">当天没有需要复习的单词。</div>';
      return;
    }

    // 按类别分组（不包括逾期）
    const todayPlanned = [];
    const extra = [];
    
    const today = new Date(dateStr);
    today.setHours(0, 0, 0, 0);
    
    items.forEach(it => {
      if (it.is_extra_review) {
        extra.push(it);
      } else if (it.next_review_date) {
        const reviewDate = new Date(it.next_review_date);
        reviewDate.setHours(0, 0, 0, 0);
        
        if (reviewDate.getTime() === today.getTime()) {
          todayPlanned.push(it);
        }
      }
    });

    const mainDiv = document.createElement('div');
    
    // 渲染今日计划
    if (todayPlanned.length > 0) {
      mainDiv.appendChild(createCategorySection('今日计划', todayPlanned, dateStr, 'primary'));
    }
    
    // 渲染额外复习
    if (extra.length > 0) {
      mainDiv.appendChild(createCategorySection('额外复习', extra, dateStr, 'warning'));
    }

    container.innerHTML = '';
    container.appendChild(mainDiv);
  }

  // 创建分类区块
  function createCategorySection(title, items, dateStr, badgeColor) {
    const section = document.createElement('div');
    section.className = 'mb-4';
    
    const header = document.createElement('h6');
    header.className = 'border-bottom pb-2 mb-3';
    header.innerHTML = `${title} <span class="badge badge-${badgeColor}">${items.length}</span>`;
    section.appendChild(header);
    
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
              ${it.unfamiliar_count > 0 ? `<span class="badge badge-warning ml-2">不熟: ${it.unfamiliar_count}</span>` : ''}
              ${it.reviewed_today ? '<span class="badge badge-success ml-2">已点评</span>' : ''}
            </p>
            <small class="text-muted">下次复习: ${it.next_review_date || '-'}</small>
          </div>
          ${!it.reviewed_today ? `
          <div class="btn-group-vertical btn-group-sm ml-3" role="group">
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
          ` : `
          <div class="ml-3">
            <span class="badge badge-success badge-lg">已完成</span>
          </div>
          `}
        </div>
      `;

      itemDiv.innerHTML = itemHtml;
      
      // 绑定反馈按钮事件（只对未点评的）
      if (!it.reviewed_today) {
        itemDiv.querySelectorAll('.btn-feedback').forEach(btn => {
          btn.addEventListener('click', function(e) {
            e.preventDefault();
            const action = this.dataset.action;
            const itemId = this.dataset.id;
            handleFeedback(action, itemId, dateStr, itemDiv);
          });
        });
      }

      list.appendChild(itemDiv);
    });
    
    section.appendChild(list);
    return section;
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
            btnGroup.innerHTML = '<span class="badge badge-success">已点评</span>';
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
    if (modal && typeof $ !== 'undefined' && $.fn.modal) {
      $(modal).on('hidden.bs.modal', function () {
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
  
  // 监听窗口大小变化
  window.addEventListener('resize', function() {
    if (calendarInstance) {
      calendarInstance.updateSize();
    }
  });

})();

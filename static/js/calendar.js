document.addEventListener('DOMContentLoaded', function() {
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

  const calendarEl = document.getElementById('calendar');
  if (!calendarEl) return;

  const calendar = new FullCalendar.Calendar(calendarEl, {
    initialView: 'dayGridMonth',
    locale: 'zh-cn',
    headerToolbar: {
      left: 'prev,next today',
      center: 'title',
      right: 'dayGridMonth,dayGridWeek'
    },
    events: function(info, successCallback, failureCallback) {
      const url = `/api/calendar-events/?start=${info.startStr}&end=${info.endStr}`;
      fetch(url, { credentials: 'same-origin' })
        .then(response => response.json())
        .then(data => successCallback(data))
        .catch(err => failureCallback(err));
    },
    dateClick: function(info) {
      openDayModal(info.dateStr);
    },
    eventClick: function(info) {
      openDayModal(info.event.startStr);
    }
  });

  calendar.render();

  function openDayModal(dateStr) {
    const modalBody = document.getElementById('calendarDayModalBody');
    const modalTitle = document.getElementById('calendarDayModalLabel');
    if (!modalBody) return;
    modalTitle.textContent = dateStr + ' 的复习';

    fetch(`/review/${dateStr}/`, {
      headers: {
        'X-Requested-With': 'XMLHttpRequest'
      },
      credentials: 'same-origin'
    })
    .then(resp => resp.text())
    .then(html => {
      modalBody.innerHTML = html;
      // show bootstrap modal
      try {
        $('#calendarDayModal').modal('show');
      } catch (e) {
        // If jQuery/Bootstrap not available, fallback: simple alert
        console.warn('Bootstrap modal not available:', e);
      }
    })
    .catch(err => console.error(err));
  }

  // When modal hides, refetch events to reflect any changes
  try {
    $('#calendarDayModal').on('hidden.bs.modal', function () {
      calendar.refetchEvents();
    });
  } catch (e) {
    // no-op
  }

});

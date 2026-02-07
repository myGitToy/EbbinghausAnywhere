/**
 * 分类管理与批量操作功能 JavaScript
 */

(function() {
    'use strict';

    // ==================== 分类筛选功能 ====================
    function initCategoryTabs() {
        const tabs = document.querySelectorAll('.category-tab:not(.add-category-btn)');
        tabs.forEach(tab => {
            tab.addEventListener('click', function(e) {
                e.preventDefault();
                const categoryId = this.dataset.categoryId;

                // 更新激活状态
                document.querySelectorAll('.category-tab').forEach(t => t.classList.remove('active'));
                this.classList.add('active');

                // 如果是全部单词，重新加载页面
                if (categoryId === '') {
                    window.location.href = '/list/';
                    return;
                }

                // 使用 AJAX 加载单词列表
                loadItems(categoryId);
            });
        });
    }

    // 加载单词列表
    function loadItems(categoryId) {
        const tbody = document.getElementById('itemTableBody');

        // 显示加载状态
        tbody.innerHTML = '<tr><td colspan="5" class="text-center">加载中...</td></tr>';

        // 调用 item_list 视图，它会检测 AJAX 请求并返回 JSON
        fetch(`/list/?category=${categoryId}`, {
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            }
        })
            .then(response => {
                if (!response.ok) {
                    throw new Error('Network response was not ok');
                }
                return response.json();
            })
            .then(data => {
                renderItems(data.items);
                updatePagination(data);
                // 更新 URL
                const newUrl = `${window.location.pathname}?category=${categoryId}`;
                window.history.pushState({category: categoryId}, '', newUrl);
            })
            .catch(error => {
                console.error('Error loading items:', error);
                tbody.innerHTML = '<tr><td colspan="5" class="text-center text-danger">加载失败，请刷新页面重试</td></tr>';
            });
    }

    // 渲染单词列表
    function renderItems(items) {
        const tbody = document.getElementById('itemTableBody');

        if (items.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" class="text-center">该分类下暂无单词</td></tr>';
            return;
        }

        tbody.innerHTML = items.map(item => `
            <tr data-item-id="${item.id}">
                <td><input type="checkbox" class="item-checkbox" data-id="${item.id}"></td>
                <td><a href="${item.detail_url}" class="text-primary">${escapeHtml(item.item)}</a></td>
                <td>${escapeHtml(item.category)}</td>
                <td>${formatDate(item.inputDate)}</td>
                <td>${item.next_review_date ? formatDate(item.next_review_date) : '未设置'}</td>
            </tr>
        `).join('');

        // 重新绑定复选框事件
        initCheckboxEvents();
    }

    // 更新分页链接
    function updatePagination(data) {
        const pagination = document.querySelector('.pagination');
        if (!pagination) return;

        const currentUrl = new URL(window.location.href);
        const categoryId = currentUrl.searchParams.get('category') || '';

        let paginationHtml = '';

        if (data.has_previous) {
            paginationHtml += `
                <li class="page-item">
                    <a class="page-link" href="?page=1${categoryId ? '&category=' + categoryId : ''}" aria-label="First">First</a>
                </li>
                <li class="page-item">
                    <a class="page-link" href="?page=${data.current_page - 1}${categoryId ? '&category=' + categoryId : ''}" aria-label="Previous">Previous</a>
                </li>
            `;
        }

        paginationHtml += `
            <li class="page-item disabled">
                <span class="page-link">
                    Page ${data.current_page} of ${data.total_pages}
                </span>
            </li>
        `;

        if (data.has_next) {
            paginationHtml += `
                <li class="page-item">
                    <a class="page-link" href="?page=${data.current_page + 1}${categoryId ? '&category=' + categoryId : ''}" aria-label="Next">Next</a>
                </li>
                <li class="page-item">
                    <a class="page-link" href="?page=${data.total_pages}${categoryId ? '&category=' + categoryId : ''}" aria-label="Last">Last</a>
                </li>
            `;
        }

        pagination.innerHTML = paginationHtml;
    }

    // ==================== 批量选择功能 ====================
    function initCheckboxEvents() {
        const selectAll = document.getElementById('selectAll');
        const itemCheckboxes = document.querySelectorAll('.item-checkbox');

        // 全选/取消全选
        if (selectAll) {
            selectAll.addEventListener('change', function() {
                document.querySelectorAll('.item-checkbox').forEach(cb => {
                    cb.checked = this.checked;
                });
                updateBatchActions();
            });
        }

        // 单个复选框变化
        itemCheckboxes.forEach(checkbox => {
            checkbox.addEventListener('change', function() {
                updateBatchActions();
            });
        });
    }

    // 更新批量操作状态
    function updateBatchActions() {
        const selected = document.querySelectorAll('.item-checkbox:checked').length;
        const selectedCount = document.getElementById('selectedCount');
        const batchActions = document.getElementById('batch-actions');

        if (selectedCount) selectedCount.textContent = selected;
        if (batchActions) {
            batchActions.style.display = selected > 0 ? 'block' : 'none';
        }

        // 更新全选复选框状态
        const selectAll = document.getElementById('selectAll');
        const allCheckboxes = document.querySelectorAll('.item-checkbox');
        if (selectAll && allCheckboxes.length > 0) {
            selectAll.checked = allCheckboxes.length === selected && selected > 0;
            selectAll.indeterminate = selected > 0 && selected < allCheckboxes.length;
        }
    }

    // 获取选中的单词 ID
    function getSelectedIds() {
        return Array.from(document.querySelectorAll('.item-checkbox:checked'))
            .map(cb => cb.dataset.id);
    }

    // ==================== 批量删除功能 ====================
    function initBatchDelete() {
        const btn = document.getElementById('batchDeleteBtn');
        if (!btn) return;

        btn.addEventListener('click', function() {
            const selectedIds = getSelectedIds();
            if (selectedIds.length === 0) {
                alert('请选择要删除的单词');
                return;
            }

            if (!confirm(`确定要删除 ${selectedIds.length} 个单词吗？此操作不可撤销。`)) {
                return;
            }

            fetch('/api/batch/delete/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCsrfToken()
                },
                body: JSON.stringify({ item_ids: selectedIds })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    alert(`成功删除 ${data.deleted_count} 个单词`);
                    location.reload();
                } else {
                    alert('删除失败: ' + (data.error || '未知错误'));
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('删除失败，请重试');
            });
        });
    }

    // ==================== 批量移动功能 ====================
    function initBatchMove() {
        const select = document.getElementById('moveToCategorySelect');
        if (!select) return;

        select.addEventListener('change', function() {
            const targetCategoryId = this.value;
            if (!targetCategoryId) return;

            const selectedIds = getSelectedIds();
            if (selectedIds.length === 0) {
                alert('请选择要移动的单词');
                this.value = '';
                return;
            }

            if (!confirm(`确定要将 ${selectedIds.length} 个单词移动到选中的分类吗？`)) {
                this.value = '';
                return;
            }

            fetch('/api/batch/move/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCsrfToken()
                },
                body: JSON.stringify({
                    item_ids: selectedIds,
                    target_category_id: targetCategoryId
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    alert(`成功移动 ${data.moved_count} 个单词`);
                    location.reload();
                } else {
                    alert('移动失败: ' + (data.error || '未知错误'));
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('移动失败，请重试');
            });
        });
    }

    // ==================== 新增分类功能 ====================
    function initAddCategory() {
        const saveBtn = document.getElementById('saveCategoryBtn');
        if (!saveBtn) return;

        saveBtn.addEventListener('click', function() {
            const nameInput = document.getElementById('newCategoryName');
            const name = nameInput.value.trim();

            if (!name) {
                alert('请输入分类名称');
                nameInput.focus();
                return;
            }

            saveBtn.disabled = true;
            saveBtn.textContent = '保存中...';

            fetch('/api/category/create/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCsrfToken()
                },
                body: JSON.stringify({ name: name })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    alert('分类创建成功');
                    location.reload();
                } else {
                    alert('创建失败: ' + (data.error || '未知错误'));
                    saveBtn.disabled = false;
                    saveBtn.textContent = '保存';
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('创建失败，请重试');
                saveBtn.disabled = false;
                saveBtn.textContent = '保存';
            });
        });

        // 清空输入框（模态框打开时）
        const modal = document.getElementById('addCategoryModal');
        if (modal) {
            modal.addEventListener('show.bs.modal', function() {
                const nameInput = document.getElementById('newCategoryName');
                nameInput.value = '';
            });
        }
    }

    // ==================== 重命名分类功能 ====================
    function initRenameCategory() {
        const saveBtn = document.getElementById('saveRenameCategoryBtn');
        if (!saveBtn) return;

        saveBtn.addEventListener('click', function() {
            const categoryId = document.getElementById('renameCategoryId').value;
            const newName = document.getElementById('renameCategoryName').value.trim();

            if (!newName) {
                alert('请输入分类名称');
                return;
            }

            saveBtn.disabled = true;
            saveBtn.textContent = '保存中...';

            fetch(`/api/category/${categoryId}/update/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCsrfToken()
                },
                body: JSON.stringify({ name: newName })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    alert('分类重命名成功');
                    location.reload();
                } else {
                    alert('重命名失败: ' + (data.error || '未知错误'));
                    saveBtn.disabled = false;
                    saveBtn.textContent = '保存';
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('重命名失败，请重试');
                saveBtn.disabled = false;
                saveBtn.textContent = '保存';
            });
        });

        // 绑定编辑按钮点击事件
        document.querySelectorAll('.btn-edit-category').forEach(btn => {
            btn.addEventListener('click', function(e) {
                e.stopPropagation();
                const categoryId = this.dataset.categoryId;
                const categoryName = this.dataset.categoryName;

                document.getElementById('renameCategoryId').value = categoryId;
                document.getElementById('renameCategoryName').value = categoryName;

                // 显示模态框
                const modal = new bootstrap.Modal(document.getElementById('renameCategoryModal'));
                modal.show();
            });
        });
    }

    // ==================== 删除分类功能 ====================
    function initDeleteCategory() {
        const confirmBtn = document.getElementById('confirmDeleteCategoryBtn');
        if (!confirmBtn) return;

        confirmBtn.addEventListener('click', function() {
            const categoryId = document.getElementById('deleteCategoryId').value;

            confirmBtn.disabled = true;
            confirmBtn.textContent = '删除中...';

            fetch(`/api/category/${categoryId}/delete/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCsrfToken()
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    const message = data.message || '分类删除成功';
                    alert(message);
                    location.reload();
                } else {
                    alert('删除失败: ' + (data.error || '未知错误'));
                    confirmBtn.disabled = false;
                    confirmBtn.textContent = '确认删除';
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('删除失败，请重试');
                confirmBtn.disabled = false;
                confirmBtn.textContent = '确认删除';
            });
        });

        // 绑定删除按钮点击事件
        document.querySelectorAll('.btn-delete-category').forEach(btn => {
            btn.addEventListener('click', function(e) {
                e.stopPropagation();
                const categoryId = this.dataset.categoryId;
                const categoryName = this.dataset.categoryName;

                document.getElementById('deleteCategoryId').value = categoryId;
                document.getElementById('deleteCategoryName').textContent = categoryName;

                // 显示模态框
                const modal = new bootstrap.Modal(document.getElementById('deleteCategoryModal'));
                modal.show();
            });
        });
    }

    // ==================== 工具函数 ====================
    function getCsrfToken() {
        const cookies = document.cookie.split(';');
        for (let cookie of cookies) {
            const [name, value] = cookie.trim().split('=');
            if (name === 'csrftoken') {
                return decodeURIComponent(value);
            }
        }
        return '';
    }

    function formatDate(dateString) {
        // 格式化日期字符串为 "Feb. 5, 2026" 格式
        if (!dateString) return '';

        const date = new Date(dateString);
        const months = [
            'Jan.', 'Feb.', 'Mar.', 'Apr.', 'May', 'Jun.',
            'Jul.', 'Aug.', 'Sep.', 'Oct.', 'Nov.', 'Dec.'
        ];

        const month = months[date.getMonth()];
        const day = date.getDate();
        const year = date.getFullYear();

        return `${month} ${day}, ${year}`;
    }

    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    // ==================== 初始化 ====================
    function init() {
        initCategoryTabs();
        initCheckboxEvents();
        initBatchDelete();
        initBatchMove();
        initAddCategory();
        initRenameCategory();
        initDeleteCategory();
    }

    // DOM 加载完成后初始化
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

})();

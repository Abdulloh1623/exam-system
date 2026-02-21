(function() {
    const injectButtons = () => {
        const nav = document.querySelector('ul.navbar-nav.ml-auto');
        
        if (nav && !document.getElementById('admin-custom-nav')) {
            const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';

            const isDark = localStorage.getItem('admin_theme') === 'dark';
            if (isDark) document.body.classList.add('dark-mode');

            const liWrapper = document.createElement('li');
            liWrapper.id = 'admin-custom-nav';
            liWrapper.className = 'nav-item d-flex align-items-center';
            liWrapper.style.gap = '10px';

            liWrapper.innerHTML = `
                <a class="nav-link" href="#" id="theme-switcher-btn" title="Rejimni almashtirish">
                    <i class="fas ${isDark ? 'fa-sun' : 'fa-moon'}"></i>
                </a>

                <form action="/accounts/logout/" method="post" id="admin-logout-form" style="display: none;">
                    <input type="hidden" name="csrfmiddlewaretoken" value="${csrfToken}">
                </form>
                
                <a class="nav-link text-danger" href="#" 
                   onclick="event.preventDefault(); document.getElementById('admin-logout-form').submit();" 
                   title="Akkauntdan chiqish">
                    <i class="fas fa-sign-out-alt"></i>
                </a>
            `;        
            
            nav.prepend(liWrapper);

            document.getElementById('theme-switcher-btn').addEventListener('click', function(e) {
                e.preventDefault();
                const body = document.body;
                const icon = this.querySelector('i');
                
                if (body.classList.contains('dark-mode')) {
                    body.classList.remove('dark-mode');
                    icon.classList.replace('fa-sun', 'fa-moon');
                    localStorage.setItem('admin_theme', 'light');
                } else {
                    body.classList.add('dark-mode');
                    icon.classList.replace('fa-moon', 'fa-sun');
                    localStorage.setItem('admin_theme', 'dark');
                }
            });
        }
    };

    setInterval(injectButtons, 500);
})();
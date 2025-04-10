document.addEventListener('DOMContentLoaded', function() {
    // Mobile menu toggle
    initMobileMenu();
    
    // Semi-circular menu
    initSemicircularMenu();
});

// Initialize mobile menu functionality
function initMobileMenu() {
    const menuToggle = document.querySelector('.menu-toggle');
    const mobileMenu = document.querySelector('.mobile-menu');
    
    if (menuToggle && mobileMenu) {
        menuToggle.addEventListener('click', function() {
            mobileMenu.classList.toggle('active');
            document.body.classList.toggle('menu-open');
            
            // Toggle hamburger icon if it exists
            const hamburgerLines = document.querySelectorAll('.hamburger-line');
            if (hamburgerLines.length) {
                hamburgerLines[0].classList.toggle('rotated');
                hamburgerLines[1].classList.toggle('hidden');
                hamburgerLines[2].classList.toggle('rotated-reverse');
            }
        });
        
        // Close mobile menu when clicking outside
        document.addEventListener('click', function(event) {
            if (mobileMenu.classList.contains('active') && 
                !mobileMenu.contains(event.target) && 
                !menuToggle.contains(event.target)) {
                mobileMenu.classList.remove('active');
                document.body.classList.remove('menu-open');
                
                // Reset hamburger icon
                const hamburgerLines = document.querySelectorAll('.hamburger-line');
                if (hamburgerLines.length) {
                    hamburgerLines[0].classList.remove('rotated');
                    hamburgerLines[1].classList.remove('hidden');
                    hamburgerLines[2].classList.remove('rotated-reverse');
                }
            }
        });
    }
}

// Initialize semi-circular menu functionality
function initSemicircularMenu() {
    const menuToggleBtn = document.querySelector('.menu-toggle-btn');
    const semicircle = document.querySelector('.semi-circle');
    const menuItems = document.querySelectorAll('.menu-item');
    
    if (menuToggleBtn && semicircle) {
        // Position menu items in a semi-circle
        positionMenuItems(menuItems);
        
        // Toggle menu open/close
        menuToggleBtn.addEventListener('click', function() {
            menuToggleBtn.classList.toggle('active');
            semicircle.classList.toggle('active');
        });
        
        // Close menu when clicking outside
        document.addEventListener('click', function(event) {
            if (semicircle.classList.contains('active') && 
                !semicircle.contains(event.target) && 
                !menuToggleBtn.contains(event.target)) {
                menuToggleBtn.classList.remove('active');
                semicircle.classList.remove('active');
            }
        });
        
        // Position tooltips
        menuItems.forEach(item => {
            const tooltip = item.querySelector('.tooltip');
            if (tooltip) {
                item.addEventListener('mouseenter', function() {
                    const rect = item.getBoundingClientRect();
                    tooltip.style.bottom = rect.height + 10 + 'px';
                    tooltip.style.left = (rect.width / 2) - (tooltip.offsetWidth / 2) + 'px';
                });
            }
        });
    }
}

// Position menu items in a semi-circle
function positionMenuItems(menuItems) {
    const itemCount = menuItems.length;
    const radius = 120; // Distance from center to menu items
    const angleRange = 120; // Degrees that the menu items will span
    const startAngle = -angleRange / 2; // Starting angle relative to the center
    
    menuItems.forEach((item, index) => {
        const angle = startAngle + (index / (itemCount - 1)) * angleRange;
        const angleInRadians = (angle * Math.PI) / 180;
        
        // Calculate position based on angle
        const x = radius * Math.cos(angleInRadians);
        const y = radius * Math.sin(angleInRadians);
        
        // Set position
        item.style.transform = `translate(${x}px, ${y}px)`;
    });
}

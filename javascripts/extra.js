/* docs/javascripts/extra.js */

document.addEventListener('DOMContentLoaded', function() {
    // 중첩된 네비게이션 항목들을 찾아서 클릭 이벤트 추가
    const nestedItems = document.querySelectorAll('.md-nav__item--nested');
    
    nestedItems.forEach(function(item) {
        const link = item.querySelector('.md-nav__link');
        
        if (link) {
            link.addEventListener('click', function(e) {
                // 링크가 실제 페이지로 이동하는 것이 아니라면 기본 동작 방지
                if (link.getAttribute('href') === '#' || !link.getAttribute('href')) {
                    e.preventDefault();
                }
                
                // 토글 기능
                item.classList.toggle('expanded');
                
                // 다른 메뉴들 닫기 (선택사항)
                nestedItems.forEach(function(otherItem) {
                    if (otherItem !== item) {
                        otherItem.classList.remove('expanded');
                    }
                });
            });
        }
    });
});


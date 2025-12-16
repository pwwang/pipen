/*
 * Assign 'docutils' class to tables so styling and
 * JavaScript behavior is applied.
 *
 * https://github.com/mkdocs/mkdocs/issues/2028
 */
(function($) {
    const searchBoxHeight = $('div.wy-side-nav-search').outerHeight(true);

    $('div.nav-scrollable-wrapper').css({
        'margin-top': searchBoxHeight + 'px',
        'height': 'calc(100vh - ' + (searchBoxHeight + 40) + 'px)'
    });
    $('div.rst-content table').addClass('docutils');
    $('div.wy-side-scroll li.toctree-l1').on('click', '>a:has(button)', function(e) {
        let $button = $(this).children('button');
        if ($button.length > 0) {
            $button.click();
        }
    });
    $('.rst-content a[href^="http"]').attr('target', '_blank');

    const $current = $('li.current,a.current').eq(0);
    if ($current.length > 0) {
        requestAnimationFrame(() => {
            $("div.nav-scrollable-wrapper").animate({
                scrollTop: $current.position().top - searchBoxHeight
            }, 750);
        });
    }
})(jQuery);

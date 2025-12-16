(function($) {
    $('div.rst-content div.section[itemprop="articleBody"]>ul>li').each(function(){
        const $li = $(this);
        let has_em = false;
        if ($li.children('em').length > 0) {
            has_em = true;
        } else if ($li.children('p:has(em)').length > 0) {
            has_em = false;
        } else {
            return;
        }
        const $em = has_em ? $li.children('em').eq(0) : $li.children('p:has(em)').eq(0).children('em').eq(0);
        try {
            const anno = $em.children('code').text().split(';');
            if (anno.includes('ns') || anno.includes('namespace') || anno.includes('choice') || anno.includes('choices')) {
                const $ul = $li.children('ul').eq(-1).hide();
                const $btn = $('<button class="ns-fold" title="Expand/Collapse content">...</button>').on('click', function(e){
                    e.preventDefault();
                    $ul.toggle();
                });
                if (has_em) {
                    let $br = $li.children('br');
                    $br = $br.length ? $br.eq(0) : $ul;
                    $btn.insertBefore($br);
                } else {
                    let $br = $em.siblings('br');
                    if ($br.length) {
                        $btn.insertBefore($br.eq(0));
                    } else {
                        $btn.appendTo($em.parent());
                    }
                }
            }
        } catch (error) { }
    });

    // $('.rst-content a[href^="http"]').attr('target', '_blank');

    if (window.location.hash !== '') {
        $(`.rst-content #faq ~ details${window.location.hash}`).attr('open', true);
    }

})(jQuery);

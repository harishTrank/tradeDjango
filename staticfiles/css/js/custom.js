$(document).ready(function () {
    $('.tab-head li').click(function () {
        var tabId = $(this).attr('data-id');
        $('#' + tabId).show().siblings().hide()
        $(this).addClass('active').siblings().removeClass('active');
    });
    $('.open-menu').click(function () {
        $(".dropdown").toggle();
    })
    $('.open-view-menu').click(function () {
        $("#view-dropdown").toggle();
    })
    $('.open-report-menu').click(function () {
        $("#report-dropdown").toggle();
    })
    $('.open-file-menu').click(function () {
        $("#file-dropdown").toggle();
    })
    $('.closeBtn').click(function () {
        $(".trades-side").hide();
        $(".trades-body").css("width", "100% - 30px");
    })
    $('#closeChangePass').click(function () {
        $(".change-pass").hide();
    })
});
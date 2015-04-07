(function ($) {
        if (!(window.console && console.log)) {
            (function() {
                var noop = function() {};
                var methods = ['assert', 'clear', 'count', 'debug', 'dir', 'dirxml', 'error', 'exception', 'group', 'groupCollapsed', 'groupEnd', 'info', 'log', 'markTimeline', 'profile', 'profileEnd', 'markTimeline', 'table', 'time', 'timeEnd', 'timeStamp', 'trace', 'warn'];
                var console = window.console = {};
                for (var i = 0; i < methods.length; i++) {
                    console[methods[i]] = noop;
                }
            }());
        }
}(jQuery));

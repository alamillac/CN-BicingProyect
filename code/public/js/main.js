var Main = (function() {

    var _private = {
        options: null,
        timeInterval: 500,

        run: function() {
            var that = this;
            for(var i = 0; i<this.options.images_data.length; i++) {
                var image_data = this.options.images_data[i];
                image_data.current_image = 0;
                setInterval(_private.image_handler, _private.timeInterval, image_data);
            }
        },

        image_handler: function(image_data) {
            var str_num_image = ("000" + image_data.current_image).slice(-4);
            var image_name = image_data.image_prefix + str_num_image + '.png';
            var src_image = image_data.image_dir + '/' + image_name;
            $(image_data.sel).attr('src', src_image);
            image_data.current_image += 1;
            image_data.current_image %= image_data.num_images;
        }
    };

    var _public = {
        init: function(options) {
            _private.options = options;
            _private.run();
        }
    };

    return _public;
})();

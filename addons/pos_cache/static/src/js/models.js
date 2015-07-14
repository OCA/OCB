openerp.pos_cache = function(instance){
    var module   = instance.point_of_sale;
    var QWeb = instance.web.qweb;
    var _t = instance.web._t;

    module.PosModel = module.PosModel.extend({
        load_server_data: function(){
            var self = this;
            var loaded = new $.Deferred();
            var progress = 0;
            var progress_step = 1.0 / self.models.length;
            var tmp = {}; // this is used to share a temporary state between models loaders

            function load_model(index){
                if(index >= self.models.length){
                    loaded.resolve();
                }else{
                    var model = self.models[index];
                    self.pos_widget.loading_message(_t('Loading')+' '+(model.label || model.model || ''), progress);
                    var fields =  typeof model.fields === 'function'  ? model.fields(self,tmp)  : model.fields;
                    var domain =  typeof model.domain === 'function'  ? model.domain(self,tmp)  : model.domain;
                    var context = typeof model.context === 'function' ? model.context(self,tmp) : model.context; 
                    var ids     = typeof model.ids === 'function'     ? model.ids(self,tmp) : model.ids;
                    progress += progress_step;
                    

                    if( model.model ){
                        if (model.model=="product.product") {
                            var records = new instance.web.Model('pos.config').call('getProductsFromCache', [self.pos_session.config_id[0]]);
                        } else {
                            if (model.ids) {
                                var records = new instance.web.Model(model.model).call('read',[ids,fields],context);
                            } else {
                                var records = new instance.web.Model(model.model).query(fields).filter(domain).context(context).all()
                            }
                        }
                        records.then(function(result){
                                try{    // catching exceptions in model.loaded(...)
                                    $.when(model.loaded(self,result,tmp))
                                        .then(function(){ load_model(index + 1); },
                                              function(err){ loaded.reject(err); });
                                }catch(err){
                                    loaded.reject(err);
                                }
                            },function(err){
                                loaded.reject(err);
                            });
                    }else if( model.loaded ){
                        try{    // catching exceptions in model.loaded(...)
                            $.when(model.loaded(self,tmp))
                                .then(  function(){ load_model(index +1); },
                                        function(err){ loaded.reject(err); });
                        }catch(err){
                            loaded.reject(err);
                        }
                    }else{
                        load_model(index + 1);
                    }
                }
            }

            try{
                load_model(0);
            }catch(err){
                loaded.reject(err);
            }

            return loaded;
        },
    });
}

class EDSRouter:
    """Envía el modelo EDS a la base de datos externa."""

    eds_models = {"EDS"}

    def _is_eds_model(self, model):
        return (
            model._meta.app_label == "hades_app" and model.__name__ in self.eds_models
        )

    def db_for_read(self, model, **hints):
        if self._is_eds_model(model):
            return "eds"
        return None

    def db_for_write(self, model, **hints):
        if self._is_eds_model(model):
            return "eds"
        return None

    def allow_relation(self, obj1, obj2, **hints):
        if self._is_eds_model(obj1.__class__) or self._is_eds_model(obj2.__class__):
            return True
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if app_label == "hades_app" and model_name == "eds":
            return db == "eds"
        if db == "eds":
            return False
        return None

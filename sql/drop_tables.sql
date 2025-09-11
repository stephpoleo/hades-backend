-- Script para borrar completamente todas las tablas de la base de datos
-- CUIDADO: Este script eliminará TODAS las tablas y sus datos

-- Borrar tablas en orden (respetando foreign keys)
DROP TABLE IF EXISTS "FormAnswers" CASCADE;
DROP TABLE IF EXISTS "WorkOrder" CASCADE;
DROP TABLE IF EXISTS "FormQuestions" CASCADE;
DROP TABLE IF EXISTS "FormTemplate" CASCADE;
DROP TABLE IF EXISTS "Users" CASCADE;
DROP TABLE IF EXISTS "EDS" CASCADE;

-- Borrar tablas de Django (sistema)
DROP TABLE IF EXISTS "auth_user" CASCADE;
DROP TABLE IF EXISTS "auth_group" CASCADE;
DROP TABLE IF EXISTS "auth_permission" CASCADE;
DROP TABLE IF EXISTS "auth_user_groups" CASCADE;
DROP TABLE IF EXISTS "auth_user_user_permissions" CASCADE;
DROP TABLE IF EXISTS "auth_group_permissions" CASCADE;
DROP TABLE IF EXISTS "django_admin_log" CASCADE;
DROP TABLE IF EXISTS "django_content_type" CASCADE;
DROP TABLE IF EXISTS "django_migrations" CASCADE;
DROP TABLE IF EXISTS "django_session" CASCADE;

-- Borrar secuencias de nuestros modelos
DROP SEQUENCE IF EXISTS "Users_id_usr_pk_seq" CASCADE;
DROP SEQUENCE IF EXISTS "EDS_id_eds_pk_seq" CASCADE;
DROP SEQUENCE IF EXISTS "FormTemplate_id_form_template_pk_seq" CASCADE;
DROP SEQUENCE IF EXISTS "FormQuestions_id_question_form_pk_seq" CASCADE;
DROP SEQUENCE IF EXISTS "FormAnswers_id_answer_form_pk_seq" CASCADE;
DROP SEQUENCE IF EXISTS "WorkOrder_id_work_order_pk_seq" CASCADE;

-- Mensaje de confirmación
SELECT 'Todas las tablas han sido eliminadas completamente.' as message;

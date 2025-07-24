-- Script para borrar completamente todas las tablas de la base de datos
-- CUIDADO: Este script eliminará TODAS las tablas y sus datos

-- Borrar tablas en orden (respetando foreign keys)
DROP TABLE IF EXISTS "FormAnswers" CASCADE;
DROP TABLE IF EXISTS "WorkOrder" CASCADE;
DROP TABLE IF EXISTS "Users" CASCADE;
DROP TABLE IF EXISTS "EDS" CASCADE;
DROP TABLE IF EXISTS "Plaza" CASCADE;
DROP TABLE IF EXISTS "FormQuestions" CASCADE;
DROP TABLE IF EXISTS "Roles" CASCADE;
DROP TABLE IF EXISTS "Permissions" CASCADE;

-- Borrar secuencias si existen
DROP SEQUENCE IF EXISTS "Users_id_usr_pk_seq" CASCADE;
DROP SEQUENCE IF EXISTS "Roles_id_rol_pk_seq" CASCADE;
DROP SEQUENCE IF EXISTS "Permissions_id_permissions_pk_seq" CASCADE;
DROP SEQUENCE IF EXISTS "WorkOrder_id_work_order_pk_seq" CASCADE;
DROP SEQUENCE IF EXISTS "EDS_id_eds_pk_seq" CASCADE;
DROP SEQUENCE IF EXISTS "Plaza_id_plaza_pk_seq" CASCADE;
DROP SEQUENCE IF EXISTS "FormQuestions_id_question_form_pk_seq" CASCADE;
DROP SEQUENCE IF EXISTS "FormAnswers_id_answer_form_pk_seq" CASCADE;

-- Mensaje de confirmación
SELECT 'Todas las tablas han sido eliminadas completamente.' as message;

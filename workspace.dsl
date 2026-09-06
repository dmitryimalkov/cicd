workspace "Test Stand" "Минимальная C4-модель тестового стенда на docker-compose" {

    model {
        user = person "Пользователь" "Обращается к приложению (APP) через браузер"

        softwareSystem = softwareSystem "Test Application" "Тестовое приложение на docker-compose" {

            nginx = container "nginx" "Reverse proxy, точка входа снаружи" "nginx" "External"
            app = container "app" "Backend-приложение" "custom build"
            postgres = container "postgres" "Основная БД" "PostgreSQL" "Database"
            redis = container "redis" "Кэш / очереди" "Redis" "Database"
            worker = container "worker" "Фоновый обработчик задач из очереди" "Python"

            user -> nginx "Открывает в браузере" "HTTPS"
            nginx -> app "Проксирует запросы" "HTTP"
            app -> postgres "Читает/пишет данные" "SQL/TCP"
            app -> redis "Кэширует данные" "Redis protocol"
            worker -> redis "Читает задачи из очереди" "Redis protocol"
        }
    }

    views {
        systemContext softwareSystem "SystemContext" {
            include *
            autoLayout
        }

        container softwareSystem "Containers" {
            include *
            autoLayout
        }

        styles {
            element "Person" {
                shape Person
                background #08427b
                color #ffffff
            }
            element "Software System" {
                background #1168bd
                color #ffffff
            }
            element "Container" {
                background #438dd5
                color #ffffff
            }
            element "Database" {
                shape Cylinder
            }
            element "External" {
                background #85bbf0
                color #000000
            }
        }
    }

}

// trigger cleanup

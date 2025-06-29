node {
    def buildNumber = env.BUILD_NUMBER
    echo "Build Number: ${buildNumber}"
    def shouldDeploy = false

    // If it is manual (not webhook)
    def isManual = false
    for (cause in currentBuild.rawBuild.getCauses()) {
        if (cause.toString().contains('UserIdCause')) {
            isManual = true
        }
    }

    stage('Checkout') {
        checkout scm
    }

    stage('Build & Push it_mk_scraper') {
        if (
            isManual ||
            (!isManual && currentBuild.changeSets.any { changeSet ->
                changeSet.items.any { item ->
                    item.affectedFiles.any { file ->
                        file.path.startsWith("scrapers/it_mk_scraper/")
                    }
                }
            })
        ) {
            shouldDeploy = true
            def imageName = "borismanev/it_mk_scraper"
            docker.withRegistry('https://registry.hub.docker.com', 'dockerhub') {
                def img = docker.build("${imageName}:${buildNumber}", "-f scrapers/it_mk_scraper/Dockerfile scrapers/it_mk_scraper")
                img.push(buildNumber)
                img.push('latest')
            }
        }
    }

    stage('Build & Push pazar3_scraper') {
        if (
            isManual ||
            (!isManual && currentBuild.changeSets.any { changeSet ->
                changeSet.items.any { item ->
                    item.affectedFiles.any { file ->
                        file.path.startsWith("scrapers/pazar3_scraper/")
                    }
                }
            })
        ) {
            shouldDeploy = true
            def imageName = "borismanev/pazar3_scraper"
            docker.withRegistry('https://registry.hub.docker.com', 'dockerhub') {
                def img = docker.build("${imageName}:${buildNumber}", "-f scrapers/pazar3_scraper/Dockerfile scrapers/pazar3_scraper")
                img.push(buildNumber)
                img.push('latest')
            }
        }
    }

    stage('Build & Push reklama5_scraper') {
        if (
            isManual ||
            (!isManual && currentBuild.changeSets.any { changeSet ->
                changeSet.items.any { item ->
                    item.affectedFiles.any { file ->
                        file.path.startsWith("scrapers/reklama5_scraper/")
                    }
                }
            })
        ) {
            shouldDeploy = true
            def imageName = "borismanev/reklama5_scraper"
            docker.withRegistry('https://registry.hub.docker.com', 'dockerhub') {
                def img = docker.build("${imageName}:${buildNumber}", "-f scrapers/reklama5_scraper/Dockerfile scrapers/reklama5_scraper")
                img.push(buildNumber)
                img.push('latest')
            }
        }
    }

    stage('Build & Push Web') {
        if (
            isManual ||
            (!isManual && currentBuild.changeSets.any { changeSet ->
                changeSet.items.any { item ->
                    item.affectedFiles.any { file ->
                        file.path.startsWith("Web/")
                    }
                }
            })
        ) {
            shouldDeploy = true
            def imageName = "borismanev/marketscraper_web"
            docker.withRegistry('https://registry.hub.docker.com', 'dockerhub') {
                def img = docker.build("${imageName}:${buildNumber}", "-f Web/Dockerfile Web")
                img.push(buildNumber)
                img.push('latest')
            }
        }
    }

    stage('Deploy to AWS EC2') {
        if (shouldDeploy) {
            sshagent(['aws-ec2-ssh']) {
                sh '''
                    ssh -o StrictHostKeyChecking=no ec2-user@16.16.178.165 '
                        cd /home/ec2-user/MarketTracker && \
                        docker compose pull && \
                        docker compose up -d
                    '
                '''
            }
        } else {
            echo "No new images built, skipping deployment."
        }
    }
}

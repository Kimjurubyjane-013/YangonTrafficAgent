/* Yangon Traffic Agent - deterministic Three.js simulation controller. */
(function () {
    'use strict';

    const TRAFFIC_SPEED = { Light: 1, Moderate: 0.72, Heavy: 0.46 };
    // Real route minutes are compressed for an interactive simulation while
    // the HUD continues to report the backend's estimated route duration.
    const TIME_COMPRESSION = 30;
    const CAMERA_LABELS = { follow: 'Follow', driver: 'Driver', top: 'Top', orbit: 'Orbit' };
    const VEHICLES = {
        Car: { color: 0x2e86de, length: 4, width: 2, height: 1.45, maxSpeed: 46, acceleration: 11, braking: 18 },
        Bus: { color: 0xf1c40f, length: 6.6, width: 2.35, height: 2.8, maxSpeed: 30, acceleration: 6, braking: 11 },
        Taxi: { color: 0xf39c12, length: 4.1, width: 2, height: 1.5, maxSpeed: 42, acceleration: 10, braking: 17 },
        Ambulance: { color: 0xffffff, length: 4.8, width: 2.1, height: 1.8, maxSpeed: 64, acceleration: 14, braking: 22 },
        'Fire Truck': { color: 0xe74c3c, length: 6.2, width: 2.4, height: 2.5, maxSpeed: 52, acceleration: 8, braking: 16 },
        Police: { color: 0x1a3c78, length: 4.3, width: 2, height: 1.55, maxSpeed: 58, acceleration: 14, braking: 21 }
    };

    function seededRandom(seed) {
        let value = seed >>> 0;
        return function () {
            value = (value * 1664525 + 1013904223) >>> 0;
            return value / 4294967296;
        };
    }

    function disposeObject(root) {
        if (!root) return;
        root.traverse((item) => {
            if (item.geometry) item.geometry.dispose();
            const materials = item.material ? (Array.isArray(item.material) ? item.material : [item.material]) : [];
            materials.forEach((material) => {
                Object.keys(material).forEach((key) => {
                    const value = material[key];
                    if (value && value.isTexture) value.dispose();
                });
                material.dispose();
            });
        });
    }

    class YangonSimulation3D {
        constructor(container, hud, controls) {
            this.container = container;
            this.hud = hud;
            this.controls = controls;
            this.ready = false;
            this.running = false;
            this.paused = false;
            this.arrived = false;
            this.cameraMode = 'follow';
            this.animationId = null;
            this.resizeObserver = null;
            this.routeGroup = null;
            this.car = null;
            this.wheels = [];
            this.clock = null;
            this.progress = 0;
            this.speed = 0;
            this.orbitAngle = 0;
            this.isDay = true;
            this.onExit = null;
            this.positionByName = {};
            this.roadSegments = [];
            this.placedObjects = [];
            this.buildingMeshes = [];
            this.worldScale = 0.02;
            this.refLat = 16.8409;
            this.refLon = 96.1735;
            this.bindControls();
        }

        bindControls() {
            if (!this.controls) return;
            this.controls.querySelector('[data-action="pause"]').addEventListener('click', () => this.togglePause());
            this.controls.querySelector('[data-action="restart"]').addEventListener('click', () => this.restart());
            this.controls.querySelector('[data-action="exit"]').addEventListener('click', () => this.exit());
            this.controls.querySelector('[data-camera]').addEventListener('change', (event) => this.setCamera(event.target.value));
            const dayNight = this.controls.querySelector('[data-action="day-night"]');
            if (dayNight) dayNight.addEventListener('click', () => this.setDayMode(!this.isDay));
        }

        init(coords, edges) {
            if (this.ready) return true;
            if (typeof THREE === 'undefined') throw new Error('Three.js library failed to load');

            this.scene = new THREE.Scene();
            this.scene.background = new THREE.Color(0x9fc7df);
            this.scene.fog = new THREE.FogExp2(0x9fc7df, 0.0015);
            this.camera = new THREE.PerspectiveCamera(58, 1, 0.1, 2500);
            this.renderer = new THREE.WebGLRenderer({ antialias: true, powerPreference: 'high-performance' });
            this.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.5));
            this.renderer.shadowMap.enabled = true;
            this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;
            this.renderer.outputEncoding = THREE.sRGBEncoding;
            this.renderer.domElement.setAttribute('aria-label', '3D vehicle route simulation');
            this.container.insertBefore(this.renderer.domElement, this.container.firstChild);

            this.hemiLight = new THREE.HemisphereLight(0xd9efff, 0x3d5132, 1.05);
            this.scene.add(this.hemiLight);
            this.sunLight = new THREE.DirectionalLight(0xfff2d0, 1.1);
            this.sunLight.position.set(-90, 160, 80);
            this.sunLight.castShadow = true;
            this.sunLight.shadow.mapSize.set(1024, 1024);
            this.sunLight.shadow.camera.left = this.sunLight.shadow.camera.bottom = -260;
            this.sunLight.shadow.camera.right = this.sunLight.shadow.camera.top = 260;
            this.scene.add(this.sunLight);

            const ground = new THREE.Mesh(
                new THREE.PlaneGeometry(3000, 3000),
                new THREE.MeshStandardMaterial({ color: 0x607b49, roughness: 1 })
            );
            ground.rotation.x = -Math.PI / 2;
            ground.position.y = -0.08;
            ground.receiveShadow = true;
            this.scene.add(ground);

            this.buildCity(coords, edges);
            this.setDayMode(true);
            this.clock = new THREE.Clock(false);
            if (typeof ResizeObserver !== 'undefined') {
                this.resizeObserver = new ResizeObserver(() => this.resize());
                this.resizeObserver.observe(this.container);
            } else {
                this.boundResize = () => this.resize();
                window.addEventListener('resize', this.boundResize);
            }
            this.ready = true;
            this.resize();
            return true;
        }

        setDayMode(day) {
            this.isDay = !!day;
            if (!this.scene) return;
            if (this.isDay) {
                this.scene.background.setHex(0x9fc7df);
                this.scene.fog.color.setHex(0x9fc7df);
                this.scene.fog.density = 0.0015;
                this.hemiLight.intensity = 1.05;
                this.sunLight.intensity = 1.1;
                this.sunLight.color.setHex(0xfff2d0);
            } else {
                this.scene.background.setHex(0x112238);
                this.scene.fog.color.setHex(0x112238);
                this.scene.fog.density = 0.0032;
                this.hemiLight.intensity = 0.56;
                this.sunLight.intensity = 0.55;
                this.sunLight.color.setHex(0x94b9ee);
            }
            const button = this.controls && this.controls.querySelector('[data-action="day-night"]');
            if (button) button.textContent = this.isDay ? 'Night' : 'Day';
        }

        project(lat, lon) {
            const earthRadius = 6371000;
            const refLatRad = this.refLat * Math.PI / 180;
            return new THREE.Vector3(
                (lon - this.refLon) * Math.PI / 180 * Math.cos(refLatRad) * earthRadius * this.worldScale,
                0,
                -(lat - this.refLat) * Math.PI / 180 * earthRadius * this.worldScale
            );
        }

        addRoad(a, b, materials) {
            const delta = b.clone().sub(a);
            const length = delta.length();
            if (length < 0.1) return;
            const angle = Math.atan2(delta.x, delta.z);
            const normal = new THREE.Vector3(-delta.z, 0, delta.x).normalize();
            this.roadSegments.push({ a: a.clone(), b: b.clone(), width: 5.6 });
            const addStrip = (width, y, material) => {
                const strip = new THREE.Mesh(new THREE.PlaneGeometry(width, length), material);
                strip.rotation.x = -Math.PI / 2;
                strip.rotation.z = -angle;
                strip.position.copy(a).add(b).multiplyScalar(0.5);
                strip.position.y = y;
                strip.receiveShadow = true;
                this.cityGroup.add(strip);
            };
            addStrip(9.4, 0.02, materials.shoulder);
            addStrip(6.4, 0.045, materials.road);
            [-3.9, 3.9].forEach((side) => {
                const perp = new THREE.Vector3(-delta.z, 0, delta.x).normalize().multiplyScalar(side);
                const walkA = a.clone().add(perp);
                const walkB = b.clone().add(perp);
                const center = walkA.add(walkB).multiplyScalar(0.5);
                const walk = new THREE.Mesh(new THREE.BoxGeometry(1.45, 0.22, length), materials.sidewalk);
                walk.position.copy(center); walk.position.y = 0.12; walk.rotation.y = angle;
                walk.receiveShadow = true; this.cityGroup.add(walk);
            });
            const dashCount = Math.max(1, Math.floor(length / 5));
            for (let i = 0; i < dashCount; i += 2) {
                const t = (i + 0.5) / dashCount;
                const dash = new THREE.Mesh(new THREE.PlaneGeometry(0.16, Math.min(2.2, length / dashCount)), materials.lane);
                dash.rotation.x = -Math.PI / 2; dash.rotation.z = -angle;
                dash.position.copy(a).lerp(b, t); dash.position.y = 0.065;
                this.cityGroup.add(dash);
            }
            for (let distance = 18; distance < length - 8; distance += 22) {
                const base = a.clone().lerp(b, distance / length);
                const side = (Math.floor(distance / 22) % 2) ? 1 : -1;
                this.addStreetLight(base.add(normal.clone().multiplyScalar(side * 5.3)));
            }
        }

        buildCity(coords, edges) {
            this.cityGroup = new THREE.Group();
            this.scene.add(this.cityGroup);
            this.roadSegments = [];
            this.placedObjects = [];
            this.buildingMeshes = [];
            Object.entries(coords).forEach(([name, value]) => { this.positionByName[name] = this.project(value[0], value[1]); });
            const materials = {
                road: new THREE.MeshStandardMaterial({ color: 0x34393e, roughness: 0.92 }),
                shoulder: new THREE.MeshStandardMaterial({ color: 0x596168, roughness: 1 }),
                sidewalk: new THREE.MeshStandardMaterial({ color: 0xb8afa1, roughness: 1 }),
                lane: new THREE.MeshBasicMaterial({ color: 0xf7e6a1 })
            };
            edges.forEach(([from, to]) => {
                if (this.positionByName[from] && this.positionByName[to]) this.addRoad(this.positionByName[from], this.positionByName[to], materials);
            });

            const random = seededRandom(20260817);
            this.buildingBounds = [];
            const palette = [0xe1c6a7, 0xb9c7d1, 0xd6b4a5, 0xc9c1a8, 0x9eb2ae, 0xd9d4c5];
            edges.forEach(([from, to], edgeIndex) => {
                const a = this.positionByName[from], b = this.positionByName[to];
                if (!a || !b) return;
                const delta = b.clone().sub(a), length = delta.length();
                const perp = new THREE.Vector3(-delta.z, 0, delta.x).normalize();
                const count = Math.min(12, Math.max(1, Math.floor(length / 14)));
                for (let i = 0; i < count; i++) {
                    const t = (i + 0.5) / count;
                    [-1, 1].forEach((side) => {
                        const width = 4 + random() * 3.5, depth = 4 + random() * 3;
                        const height = 5 + random() * (edgeIndex % 3 === 0 ? 22 : 12);
                        const center = a.clone().lerp(b, t).add(perp.clone().multiplyScalar(side * (9 + depth * 0.5 + random() * 4)));
                        const footprint = Math.hypot(width, depth) * 0.55;
                        if (!this.isPlacementClear(center, footprint, 5.8)) return;
                        const building = new THREE.Mesh(
                            new THREE.BoxGeometry(width, height, depth),
                            new THREE.MeshStandardMaterial({ color: palette[Math.floor(random() * palette.length)], roughness: 0.86 })
                        );
                        building.position.set(center.x, height / 2, center.z);
                        building.rotation.y = Math.atan2(delta.x, delta.z) + (random() - 0.5) * 0.1;
                        building.castShadow = building.receiveShadow = true;
                        this.cityGroup.add(building);
                        building.updateMatrixWorld(true);
                        this.buildingBounds.push(new THREE.Box3().setFromObject(building));
                        this.buildingMeshes.push(building);
                        this.placedObjects.push({ position: center.clone(), radius: footprint + 0.8 });
                        if (i % 2 === 0) {
                            const treePosition = center.clone().add(perp.clone().multiplyScalar(side * (depth * 0.6 + 2.2)));
                            if (this.isPlacementClear(treePosition, 1.25, 5.4)) {
                                this.addTree(treePosition);
                                this.placedObjects.push({ position: treePosition.clone(), radius: 1.4 });
                            }
                        }
                    });
                }
            });

            Object.entries(this.positionByName).forEach(([name, position]) => {
                const junction = new THREE.Mesh(
                    new THREE.CylinderGeometry(4.7, 4.7, 0.1, 24),
                    new THREE.MeshStandardMaterial({ color: 0x3a3f44, roughness: 1 })
                );
                junction.position.copy(position); junction.position.y = 0.055; junction.receiveShadow = true;
                this.cityGroup.add(junction);
                this.addStreetLight(position.clone().add(new THREE.Vector3(5.2, 0, 5.2)));
                if (/Sule|Shwedagon|Pagoda/i.test(name)) this.addPagodaHint(position.clone().add(new THREE.Vector3(10, 0, -10)));
            });
        }

        addTree(position) {
            const group = new THREE.Group();
            const trunk = new THREE.Mesh(new THREE.CylinderGeometry(0.18, 0.26, 2.4, 7), new THREE.MeshStandardMaterial({ color: 0x725034 }));
            trunk.position.y = 1.2;
            const crown = new THREE.Mesh(new THREE.SphereGeometry(1.25, 8, 6), new THREE.MeshStandardMaterial({ color: 0x337447, roughness: 1 }));
            crown.position.y = 3;
            group.add(trunk, crown); group.position.copy(position); group.traverse((item) => { item.castShadow = true; });
            this.cityGroup.add(group);
        }

        isPlacementClear(position, radius, roadClearance) {
            for (const road of this.roadSegments) {
                if (this.distanceToSegment(position, road.a, road.b) < roadClearance + radius) return false;
            }
            for (const item of this.placedObjects) {
                if (item.position.distanceTo(position) < item.radius + radius) return false;
            }
            return true;
        }

        distanceToSegment(point, a, b) {
            const ab = b.clone().sub(a);
            const lengthSq = ab.lengthSq();
            if (!lengthSq) return point.distanceTo(a);
            const t = Math.max(0, Math.min(1, point.clone().sub(a).dot(ab) / lengthSq));
            return point.distanceTo(a.clone().add(ab.multiplyScalar(t)));
        }

        addStreetLight(position) {
            const group = new THREE.Group();
            const poleMat = new THREE.MeshStandardMaterial({ color: 0x3c4650, metalness: 0.5, roughness: 0.45 });
            const pole = new THREE.Mesh(new THREE.CylinderGeometry(0.08, 0.12, 4.5, 8), poleMat);
            pole.position.y = 2.25;
            const lamp = new THREE.Mesh(new THREE.SphereGeometry(0.22, 8, 6), new THREE.MeshBasicMaterial({ color: 0xffedb3 }));
            lamp.position.y = 4.5; group.add(pole, lamp); group.position.copy(position); this.cityGroup.add(group);
        }

        addPagodaHint(position) {
            const group = new THREE.Group();
            const gold = new THREE.MeshStandardMaterial({ color: 0xd9a928, metalness: 0.45, roughness: 0.35 });
            [3.8, 2.8, 1.9].forEach((radius, index) => {
                const tier = new THREE.Mesh(new THREE.CylinderGeometry(radius * 0.72, radius, 0.7, 16), gold);
                tier.position.y = 0.35 + index * 0.65; group.add(tier);
            });
            const spire = new THREE.Mesh(new THREE.ConeGeometry(1.5, 7, 18), gold); spire.position.y = 5.2; group.add(spire);
            group.position.copy(position); group.traverse((item) => { item.castShadow = true; }); this.cityGroup.add(group);
        }

        createVehicle(type) {
            if (this.car) { this.scene.remove(this.car); disposeObject(this.car); }
            const spec = VEHICLES[type] || VEHICLES.Car;
            const group = new THREE.Group();
            const bodyMaterial = new THREE.MeshStandardMaterial({ color: spec.color, metalness: 0.22, roughness: 0.55 });
            const body = new THREE.Mesh(new THREE.BoxGeometry(spec.width, spec.height * 0.55, spec.length), bodyMaterial);
            body.position.y = 0.55 + spec.height * 0.25; body.castShadow = true; group.add(body);
            const cabin = new THREE.Mesh(
                new THREE.BoxGeometry(spec.width * 0.78, spec.height * 0.45, spec.length * 0.46),
                new THREE.MeshStandardMaterial({ color: 0x263746, metalness: 0.3, roughness: 0.25 })
            );
            cabin.position.set(0, spec.height * 0.76, -spec.length * 0.08); cabin.castShadow = true; group.add(cabin);
            const wheelGeometry = new THREE.CylinderGeometry(0.43, 0.43, 0.34, 14);
            const wheelMaterial = new THREE.MeshStandardMaterial({ color: 0x15181b, roughness: 0.9 });
            this.wheels = [];
            [-1, 1].forEach((xSide) => [-1, 1].forEach((zSide) => {
                const wheel = new THREE.Mesh(wheelGeometry, wheelMaterial);
                wheel.rotation.z = Math.PI / 2;
                wheel.position.set(xSide * spec.width * 0.52, 0.43, zSide * spec.length * 0.31);
                group.add(wheel); this.wheels.push(wheel);
            }));
            group.userData.spec = spec; this.car = group; this.scene.add(group);
        }

        createRibbon(points, width, y, material) {
            const positions = [];
            const indices = [];
            for (let i = 0; i < points.length; i++) {
                const previous = points[Math.max(0, i - 1)];
                const next = points[Math.min(points.length - 1, i + 1)];
                const tangent = next.clone().sub(previous).setY(0).normalize();
                const normal = new THREE.Vector3(-tangent.z, 0, tangent.x).multiplyScalar(width / 2);
                const left = points[i].clone().add(normal); left.y = y;
                const right = points[i].clone().sub(normal); right.y = y;
                positions.push(left.x, left.y, left.z, right.x, right.y, right.z);
                if (i < points.length - 1) {
                    const base = i * 2;
                    indices.push(base, base + 2, base + 1, base + 1, base + 2, base + 3);
                }
            }
            const geometry = new THREE.BufferGeometry();
            geometry.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
            geometry.setIndex(indices); geometry.computeVertexNormals();
            const mesh = new THREE.Mesh(geometry, material);
            mesh.receiveShadow = true;
            return mesh;
        }

        createRoute(routeNames, traffic, routeLegs) {
            if (this.routeGroup) { this.scene.remove(this.routeGroup); disposeObject(this.routeGroup); }
            this.routeGroup = new THREE.Group(); this.scene.add(this.routeGroup);
            const projectedLegs = Array.isArray(routeLegs) && routeLegs.length === routeNames.length - 1
                ? routeLegs.map(leg => leg.map(([lat, lon]) => this.project(lat, lon)).filter(
                    (point, index, all) => index === 0 || point.distanceTo(all[index - 1]) > 0.025
                ))
                : routeNames.slice(0, -1).map((name, index) => [
                    this.positionByName[name].clone(), this.positionByName[routeNames[index + 1]].clone()
                ]);
            const points = projectedLegs.flatMap((leg, index) => index === 0 ? leg : leg.slice(1));
            if (points.length < 2) throw new Error('Route requires at least two valid waypoints');

            // Arc-length traversal of the OSRM polyline stays on the road exactly.
            // Heading interpolation below smooths steering without a spline that
            // could cut across the inside of a sharp street corner.
            this.routeCurve = new THREE.CurvePath();
            points.slice(0, -1).forEach((point, index) => {
                this.routeCurve.add(new THREE.LineCurve3(point, points[index + 1]));
            });
            this.totalLength = this.routeCurve.getLength();

            // Procedural objects are decorative rather than geographically
            // authoritative. Hide any building that conflicts with the real road.
            this.buildingMeshes.forEach(building => {
                building.visible = true;
                const box = new THREE.Box3().setFromObject(building);
                const size = box.getSize(new THREE.Vector3());
                const center = box.getCenter(new THREE.Vector3());
                const clearance = Math.max(size.x, size.z) * 0.5 + 4.2;
                building.visible = !points.slice(0, -1).some((point, index) =>
                    this.distanceToSegment(center, point, points[index + 1]) < clearance
                );
            });

            const legChordLengths = projectedLegs.map(leg => leg.slice(0, -1).reduce(
                (sum, point, index) => sum + point.distanceTo(leg[index + 1]), 0
            ));
            const chordTotal = legChordLengths.reduce((sum, length) => sum + length, 0);
            this.segmentLengths = legChordLengths.map(length => this.totalLength * length / Math.max(chordTotal, 0.001));
            this.segmentStarts = [0];
            this.segmentLengths.forEach((length) => this.segmentStarts.push(this.segmentStarts[this.segmentStarts.length - 1] + length));

            const shoulderMaterial = new THREE.MeshStandardMaterial({ color: 0x9aa1a7, roughness: 0.95 });
            const asphaltMaterial = new THREE.MeshStandardMaterial({ color: 0x30343a, roughness: 0.9 });
            this.routeGroup.add(this.createRibbon(points, 7.4, 0.015, shoulderMaterial));
            this.routeGroup.add(this.createRibbon(points, 5.8, 0.025, asphaltMaterial));

            projectedLegs.forEach((leg, index) => {
                const color = { Light: 0x2ecc71, Moderate: 0xf39c12, Heavy: 0xe74c3c }[traffic[index]] || 0x21c7f3;
                this.routeGroup.add(this.createRibbon(
                    leg, 0.34, 0.045,
                    new THREE.MeshBasicMaterial({ color, transparent: true, opacity: 0.9 })
                ));
            });

            // Traffic-colored markers keep segment conditions visible without
            // breaking the continuous navigation ribbon.
            this.segmentStarts.slice(0, -1).forEach((start, index) => {
                const t = start / Math.max(this.totalLength, 0.001);
                const marker = new THREE.Mesh(
                    new THREE.SphereGeometry(0.35, 10, 8),
                    new THREE.MeshBasicMaterial({ color: { Light: 0x2ecc71, Moderate: 0xf39c12, Heavy: 0xe74c3c }[traffic[index]] || 0xffffff })
                );
                marker.position.copy(this.routeCurve.getPointAt(Math.min(1, t))); marker.position.y = 0.35;
                this.routeGroup.add(marker);
            });
        }

        start(options) {
            this.init(options.coords, options.edges);
            this.stopLoop();
            this.routeNames = options.routeNames.slice();
            this.traffic = options.traffic.slice();
            this.vehicleType = options.vehicle;
            this.estimatedMinutes = Number(options.estimatedMinutes) || 1;
            this.routeLegs = Array.isArray(options.routeLegs) ? options.routeLegs.map(leg => leg.map(point => point.slice())) : null;
            this.createRoute(this.routeNames, this.traffic, this.routeLegs);
            this.createVehicle(this.vehicleType);
            this.progress = 0; this.speed = 0; this.paused = false; this.arrived = false; this.running = true;
            this.controls.classList.add('visible');
            this.controls.querySelector('[data-action="pause"]').textContent = 'Pause';
            this.clock.start(); this.updatePose(0, 0, 0); this.loop();
        }

        getSegment(distance) {
            for (let i = 0; i < this.segmentLengths.length; i++) {
                if (distance <= this.segmentStarts[i + 1] || i === this.segmentLengths.length - 1) {
                    return { index: i, local: Math.max(0, Math.min(1, (distance - this.segmentStarts[i]) / this.segmentLengths[i])) };
                }
            }
            return { index: 0, local: 0 };
        }

        updatePose(distance, delta, wheelDistance) {
            const segment = this.getSegment(distance);
            if (!this.routeCurve) return;
            const routeT = Math.max(0, Math.min(1, distance / Math.max(this.totalLength, 0.001)));
            const point = this.routeCurve.getPointAt(routeT);
            const tangent = this.routeCurve.getTangentAt(Math.min(0.9999, routeT)).normalize();
            this.car.position.copy(point); this.car.position.y = 0.045;
            const targetAngle = Math.atan2(tangent.x, tangent.z);
            const current = this.car.rotation.y;
            this.car.rotation.y = current + Math.atan2(Math.sin(targetAngle - current), Math.cos(targetAngle - current)) * Math.min(1, delta * 7);
            this.wheels.forEach((wheel) => { wheel.rotation.x -= (wheelDistance || 0) / 0.43; });
            this.updateCamera(point, tangent, delta);
            this.updateHud(segment.index, distance);
        }

        updateCamera(point, tangent, delta) {
            const spec = this.car.userData.spec;
            const side = new THREE.Vector3(tangent.z, 0, -tangent.x);
            let desired, lookAt;
            if (this.cameraMode === 'driver') {
                desired = point.clone().add(new THREE.Vector3(0, spec.height * 0.95, 0)).add(tangent.clone().multiplyScalar(spec.length * 0.25));
                lookAt = desired.clone().add(tangent.clone().multiplyScalar(18));
            } else if (this.cameraMode === 'top') {
                desired = point.clone().add(new THREE.Vector3(0, 52, 0.1)); lookAt = point;
            } else if (this.cameraMode === 'orbit') {
                this.orbitAngle += delta * 0.22;
                desired = point.clone().add(new THREE.Vector3(Math.sin(this.orbitAngle) * 20, 12, Math.cos(this.orbitAngle) * 20)); lookAt = point.clone().add(new THREE.Vector3(0, 1, 0));
            } else {
                desired = point.clone().add(tangent.clone().multiplyScalar(-14)).add(side.clone().multiplyScalar(1.5)).add(new THREE.Vector3(0, 7, 0));
                lookAt = point.clone().add(tangent.clone().multiplyScalar(7)).add(new THREE.Vector3(0, 1.3, 0));
            }
            desired.y = Math.max(desired.y, 1.2);
            // Keep cameras out of the deterministic building volumes. Moving the
            // camera above a roof is less disorienting than an abrupt lateral jump.
            const collision = this.buildingBounds && this.buildingBounds.find((box) =>
                desired.x >= box.min.x - 0.7 && desired.x <= box.max.x + 0.7 &&
                desired.y >= box.min.y - 0.7 && desired.y <= box.max.y + 0.7 &&
                desired.z >= box.min.z - 0.7 && desired.z <= box.max.z + 0.7
            );
            if (collision) desired.y = Math.max(desired.y, collision.max.y + 2.5);
            this.camera.position.lerp(desired, 1 - Math.exp(-delta * 5));
            if (!this.cameraLookAt) this.cameraLookAt = lookAt.clone();
            this.cameraLookAt.lerp(lookAt, 1 - Math.exp(-delta * 7)); this.camera.lookAt(this.cameraLookAt);
        }

        updateHud(segmentIndex, distance) {
            const remainingWorld = Math.max(0, this.totalLength - distance);
            const routeKm = Number(window.currentSimulationDistanceKm) || this.totalLength / 20;
            const remainingKm = this.totalLength ? routeKm * remainingWorld / this.totalLength : 0;
            const etaMinutes = Math.max(0, this.estimatedMinutes * (1 - this.progress));
            const road = `${this.routeNames[segmentIndex]} → ${this.routeNames[segmentIndex + 1]}`;
            const values = {
                speed: `${Math.round(this.speed * 3.6)} km/h`, traffic: this.traffic[segmentIndex] || 'Light',
                road, progress: `${Math.round(this.progress * 100)}%`, remaining: `${remainingKm.toFixed(1)} km`,
                eta: this.arrived ? 'Arrived' : (etaMinutes < 1 ? `${Math.max(1, Math.ceil(etaMinutes * 60))} sec` : `${Math.ceil(etaMinutes)} min`),
                camera: CAMERA_LABELS[this.cameraMode],
                state: this.arrived ? 'Arrived' : (this.paused ? 'Paused' : 'Driving')
            };
            Object.entries(values).forEach(([key, value]) => {
                const element = this.hud.querySelector(`[data-hud="${key}"]`); if (element) element.textContent = value;
            });
            this.hud.classList.add('visible');
        }

        loop() {
            const frame = () => {
                if (!this.running) return;
                const delta = Math.min(this.clock.getDelta(), 0.05);
                if (!this.paused && !this.arrived) {
                    const distance = this.progress * this.totalLength;
                    const segment = this.getSegment(distance);
                    const spec = this.car.userData.spec;
                    const trafficFactor = TRAFFIC_SPEED[this.traffic[segment.index]] || 1;
                    const before = this.routeCurve.getTangentAt(Math.max(0, this.progress - 0.025));
                    const after = this.routeCurve.getTangentAt(Math.min(0.9999, this.progress + 0.025));
                    const turnFactor = Math.max(0.48, 1 - before.angleTo(after) * 1.5);
                    const junctionDistance = Math.min(segment.local, 1 - segment.local);
                    const junctionFactor = junctionDistance < 0.09 ? 0.58 + junctionDistance * 4.6 : 1;
                    const arrivalFactor = this.progress > 0.94 ? Math.max(0.2, (1 - this.progress) / 0.06) : 1;
                    const targetSpeed = (spec.maxSpeed / 3.6) * trafficFactor * turnFactor * junctionFactor * arrivalFactor;
                    const rate = targetSpeed > this.speed ? spec.acceleration : spec.braking;
                    this.speed += Math.sign(targetSpeed - this.speed) * Math.min(Math.abs(targetSpeed - this.speed), rate * delta);
                    const worldDistance = this.speed * delta * TIME_COMPRESSION * this.worldScale;
                    this.progress = Math.min(1, this.progress + worldDistance / Math.max(this.totalLength, 0.001));
                    this.updatePose(this.progress * this.totalLength, delta, worldDistance);
                    if (this.progress >= 1) {
                        this.arrived = true; this.speed = 0; this.updatePose(this.totalLength, delta, 0);
                        if (this.hud) this.hud.classList.add('arrived');
                    }
                } else if (this.car) {
                    this.updateCamera(this.car.position, new THREE.Vector3(Math.sin(this.car.rotation.y), 0, Math.cos(this.car.rotation.y)), delta);
                }
                this.renderer.render(this.scene, this.camera);
                this.animationId = requestAnimationFrame(frame);
            };
            this.animationId = requestAnimationFrame(frame);
        }

        togglePause() {
            if (!this.running || this.arrived) return;
            this.paused = !this.paused;
            this.controls.querySelector('[data-action="pause"]').textContent = this.paused ? 'Resume' : 'Pause';
        }

        restart() { if (this.routeNames) this.start({ coords: window.LOCATION_COORDS_FOR_SIM, edges: window.GRAPH_EDGES_FOR_SIM, routeNames: this.routeNames, traffic: this.traffic, routeLegs: this.routeLegs, vehicle: this.vehicleType, estimatedMinutes: this.estimatedMinutes }); }
        setCamera(mode) { if (CAMERA_LABELS[mode]) { this.cameraMode = mode; this.cameraLookAt = null; } }
        stopLoop() { if (this.animationId !== null) cancelAnimationFrame(this.animationId); this.animationId = null; this.running = false; if (this.clock) this.clock.stop(); }
        exit() { this.stopLoop(); this.paused = false; if (this.onExit) this.onExit(); }
        resize() {
            if (!this.renderer || this.container.offsetParent === null) return;
            const width = Math.max(1, this.container.clientWidth), height = Math.max(1, this.container.clientHeight);
            this.camera.aspect = width / height; this.camera.updateProjectionMatrix(); this.renderer.setSize(width, height, false);
        }
        reset() {
            this.stopLoop(); this.progress = 0; this.speed = 0; this.arrived = false;
            if (this.hud) { this.hud.classList.remove('visible', 'arrived'); }
            if (this.controls) this.controls.classList.remove('visible');
            if (this.routeGroup) { this.scene.remove(this.routeGroup); disposeObject(this.routeGroup); this.routeGroup = null; }
            if (this.car) { this.scene.remove(this.car); disposeObject(this.car); this.car = null; this.wheels = []; }
            this.routeCurve = null;
            this.segmentLengths = [];
            this.segmentStarts = [0];
        }
        destroy() {
            this.reset(); if (this.resizeObserver) this.resizeObserver.disconnect();
            if (this.boundResize) window.removeEventListener('resize', this.boundResize);
            if (this.scene) disposeObject(this.scene); if (this.renderer) { this.renderer.dispose(); this.renderer.domElement.remove(); }
            this.ready = false;
        }
    }

    window.YangonSimulation3D = YangonSimulation3D;
}());

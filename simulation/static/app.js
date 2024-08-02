document.addEventListener('DOMContentLoaded', () => {
    const config = {
        type: Phaser.AUTO,
        width: 1152,
        height: 1152,
        parent: 'game-container',
        pixelArt: true,  // Enable pixel art mode to prevent blurring
        scene: {
            preload: preload,
            create: create,
            update: update
        }
    };

    const game = new Phaser.Game(config);
    let gridData = [];
    const spriteSize = 64;

    function preload() {
        // Preload the sprite sheet
        this.load.spritesheet('sprites', '/static/spritesheet.png', {
            frameWidth: spriteSize,
            frameHeight: spriteSize
        });
    }

    function create() {
        // Fetch the initial data
        fetchGridData();
        
        // Set camera zoom to 2x
        //this.cameras.main.setZoom(2);


    }

    function update() {
        // Clear the scene before rendering
        this.children.removeAll();

        // Add a black background
        this.add.rectangle(0, 0, 800, 600, 0x000000).setOrigin(0);

        // Render the grid
        gridData.forEach(cell => {
            let frame;
            if (cell.sprite === 'empty') frame = 1; // Assuming 'grass.png' is at position (1, 0)
            else if (cell.sprite === 'red') frame = 2; // Assuming 'knight1.png' is at position (2, 0)
            else if (cell.sprite === 'blue') frame = 3; // Assuming 'knight2.png' is at position (3, 0)
            else if (cell.sprite === 'wall') frame = 4; // Assuming 'rock.png' is at position (4, 0)
            else if (cell.sprite === 'gold') frame = 0; // Assuming 'gold.png' is at position (0, 0)
            else if (cell.sprite === 'trove') frame = 5; // Assuming 'trove.png' is at position (0, 1)
            else if (cell.sprite === 'wumpus') frame = 6; // Assuming 'wumpus.png' is at position (1, 1)
            else alert('Unknown sprite: ' + cell.sprite);

            // Make it double the size. The sprite sheet is 64x64, so we need to multiply by 2. Also scale the sprite.
            //this.add.image(cell.x * 50, cell.y * 50, 'sprites', frame).setOrigin(0);
            this.add.image(cell.x * spriteSize * 2, cell.y * spriteSize * 2, 'sprites', frame).setOrigin(0).setScale(2);
        });
    }

    function fetchGridData() {
        fetch('/api/renderer/data')
            .then(response => response.json())
            .then(data => {
                gridData = data.grid_cells;
            })
            .catch(error => console.error('Error fetching grid data:', error));
    }

    setInterval(fetchGridData, 10);  // Update the data every n milliseconds.
});

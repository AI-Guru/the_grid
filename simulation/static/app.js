document.addEventListener('DOMContentLoaded', () => {
    const config = {
        type: Phaser.AUTO,
        width: 800,
        height: 600,
        parent: 'game-container',
        scene: {
            preload: preload,
            create: create,
            update: update
        }
    };

    const game = new Phaser.Game(config);
    let gridData = [];

    function preload() {
        // Preload assets if necessary
    }

    function create() {
        // Fetch the initial data
        fetchGridData();
    }

    function update() {
        // Clear the scene before rendering
        this.children.removeAll();

        // Render the grid
        gridData.forEach(cell => {
            let color = 0x00ff00; // Default to green for 'grass'
            if (cell.sprite === 'red') color = 0xff0000;
            if (cell.sprite === 'blue') color = 0x0000ff;

            this.add.rectangle(cell.x * 50, cell.y * 50, 50, 50, color).setOrigin(0);
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

    setInterval(fetchGridData, 1000);  // Update the data every second
});

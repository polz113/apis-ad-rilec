<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

class CreateADgroupsTable extends Migration
{
    /**
     * Run the migrations.
     *
     * @return void
     */
    public function up()
    {
        Schema::create('a_d_groups', function (Blueprint $table) {
            $table->id();
            $table->timestamps();
            $table->foreignId('dataset')->constrained('a_d_datasets');
            $table->string('name');
            $table->foreignId('parent')->constrained('a_d_groups')->nullable();
        });
    }

    /**
     * Reverse the migrations.
     *
     * @return void
     */
    public function down()
    {
        Schema::dropIfExists('a_d_groups');
    }
}
